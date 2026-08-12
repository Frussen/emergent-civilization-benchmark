"""Deterministic, headless M0 simulation kernel."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable, Mapping
from enum import Enum
from functools import cache
from importlib.metadata import PackageNotFoundError, version
from math import isfinite
from pathlib import Path

from ecb.config import SimulationConfig
from ecb.model import (
    Action,
    ActionKind,
    AgentId,
    AgentState,
    CellState,
    DeathEvent,
    HarvestEvent,
    InvalidActionEvent,
    Observation,
    ObservedCell,
    ResourceState,
    RunLog,
    SimulationNumericalError,
    TickMetrics,
    VisibleAgent,
    WorldEvent,
    WorldState,
)
from ecb.policies import Policy
from ecb.rng import SeededRNG

PolicyFactory = Callable[[AgentId], Policy]
type JsonValue = (
    None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
)


@cache
def _software_version() -> str:
    try:
        package_version = version("emergent-civilization-benchmark")
    except PackageNotFoundError:
        package_version = "0.1.0"
    source_directory = Path(__file__).resolve().parent
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            cwd=source_directory,
            text=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            check=True,
            capture_output=True,
            cwd=source_directory,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return package_version
    suffix = "+dirty" if dirty else ""
    return f"{package_version}+{revision}{suffix}"


class Simulation:
    """Own world transitions while exposing only observations to policies."""

    def __init__(
        self,
        config: SimulationConfig = SimulationConfig(),
        seed: int = 0,
        policy_factory: PolicyFactory | None = None,
        *,
        agent_ids: tuple[AgentId, ...] | None = None,
    ) -> None:
        self.config = config
        self._initialization_rng = SeededRNG(self._derived_seed(seed, "initialization"))
        self._resolution_rng = SeededRNG(self._derived_seed(seed, "resolution"))
        if policy_factory is None:
            raise ValueError("policy_factory must be supplied explicitly")
        ids = (
            tuple(
                f"agent-{index:06d}"
                for index in range(config.initial_population)
            )
            if agent_ids is None
            else agent_ids
        )
        if len(ids) != config.initial_population:
            raise ValueError("agent ID count must match initial_population")
        if len(set(ids)) != len(ids):
            raise ValueError("agent IDs must be unique")

        self.world = self._initial_world(tuple(sorted(ids)))
        self.policies = {
            agent_id: policy_factory(agent_id)
            for agent_id in sorted(self.world.agents)
        }
        if len({id(policy) for policy in self.policies.values()}) != len(self.policies):
            raise ValueError("each agent must own a distinct policy instance")
        self.policy_rngs = {
            agent_id: SeededRNG(self._derived_seed(seed, f"policy:{agent_id}"))
            for agent_id in sorted(self.world.agents)
        }
        policy_identities = {
            agent_id: self._policy_identity(policy)
            for agent_id, policy in self.policies.items()
        }
        policy_configurations = {
            agent_id: self._canonicalize(policy.configuration_state())
            for agent_id, policy in self.policies.items()
        }
        self.log = RunLog(
            seed=seed,
            configuration=config.as_dict(),
            software_version=_software_version(),
            initial_agent_ids=tuple(sorted(ids)),
            policy_identities=policy_identities,
            policy_configurations=policy_configurations,
        )
        self.initial_population = config.initial_population
        self.world.verify_invariants()

    @staticmethod
    def _derived_seed(seed: int, purpose: str) -> int:
        encoded = f"ecb-m0:{seed}:{purpose}".encode()
        return int.from_bytes(hashlib.sha256(encoded).digest(), "big")

    def _initial_world(self, agent_ids: tuple[AgentId, ...]) -> WorldState:
        config = self.config
        cells = {
            (x, y): CellState(
                food=ResourceState(
                    stock=config.food_initial_stock,
                    capacity=config.food_capacity,
                    regeneration_rate=config.food_regeneration_rate,
                ),
                water=ResourceState(
                    stock=config.water_initial_stock,
                    capacity=config.water_capacity,
                    regeneration_rate=config.water_regeneration_rate,
                ),
            )
            for x in range(config.width)
            for y in range(config.height)
        }
        agents = {}
        for agent_id in agent_ids:
            position = (
                self._initialization_rng.randint(0, config.width - 1),
                self._initialization_rng.randint(0, config.height - 1),
            )
            agents[agent_id] = AgentState(
                id=agent_id,
                position=position,
                food_inventory=config.initial_food_inventory,
                water_inventory=config.initial_water_inventory,
                health=config.initial_health,
                food_productivity=config.food_productivity,
                water_productivity=config.water_productivity,
            )
        return WorldState(config.width, config.height, cells, agents)

    def observe(
        self,
        agent_id: AgentId,
        _occupancy: Mapping[tuple[int, int], tuple[AgentState, ...]] | None = None,
    ) -> Observation:
        agent = self.world.agents[agent_id]
        if not agent.alive:
            raise ValueError("dead agents do not receive observations")

        radius = self.config.observation_radius
        ax, ay = agent.position
        cells: list[ObservedCell] = []
        for x in range(max(0, ax - radius), min(self.world.width, ax + radius + 1)):
            for y in range(
                max(0, ay - radius), min(self.world.height, ay + radius + 1)
            ):
                cell = self.world.cells[(x, y)]
                cells.append(
                    ObservedCell(
                        relative_position=(x - ax, y - ay),
                        food_stock=cell.food.stock,
                        water_stock=cell.water.stock,
                    )
                )

        occupancy = _occupancy or self._occupancy()
        visible_agents = tuple(
            VisibleAgent(id=other.id, relative_position=(x - ax, y - ay))
            for x in range(max(0, ax - radius), min(self.world.width, ax + radius + 1))
            for y in range(
                max(0, ay - radius), min(self.world.height, ay + radius + 1)
            )
            for other in occupancy.get((x, y), ())
            if other.id != agent.id
        )
        return Observation(
            own_id=agent.id,
            position=agent.position,
            health=agent.health,
            food_inventory=agent.food_inventory,
            water_inventory=agent.water_inventory,
            food_productivity=agent.food_productivity,
            water_productivity=agent.water_productivity,
            cells=tuple(cells),
            visible_agents=visible_agents,
        )

    def _occupancy(self) -> dict[tuple[int, int], tuple[AgentState, ...]]:
        grouped: dict[tuple[int, int], list[AgentState]] = {}
        for agent in self.world.living_agents():
            grouped.setdefault(agent.position, []).append(agent)
        return {position: tuple(agents) for position, agents in grouped.items()}

    def step(self, actions: Mapping[AgentId, Action] | None = None) -> TickMetrics:
        """Advance exactly one tick, optionally using recorded external actions."""
        living_ids = tuple(agent.id for agent in self.world.living_agents())
        occupancy = self._occupancy()
        selected: dict[AgentId, Action] = {}
        if actions is not None:
            missing = sorted(set(living_ids) - set(actions))
            if missing:
                raise ValueError(
                    "external action map is missing living agents: "
                    + ", ".join(missing)
                )
        for agent_id in living_ids:
            if actions is None:
                selected[agent_id] = self.policies[agent_id].decide(
                    self.observe(agent_id, occupancy), self.policy_rngs[agent_id]
                )
            else:
                selected[agent_id] = actions[agent_id]
            if not isinstance(selected[agent_id], Action):
                raise TypeError("policies and external maps must supply Action objects")

        tick_events: list[WorldEvent] = []
        self._validate_numerical_transition(selected)
        self._resolve_movement(selected, tick_events)
        self._resolve_harvesting(selected, tick_events)
        self._apply_metabolism(tick_events)
        self._regenerate_resources()
        self.world.tick += 1

        living = len(self.world.living_agents())
        denominator = self.initial_population
        survival_fraction = living / denominator if denominator else 1.0
        metrics = TickMetrics(self.world.tick, living, survival_fraction)
        self.log.actions.extend(
            (self.world.tick - 1, agent_id, selected[agent_id])
            for agent_id in living_ids
        )
        self.log.events.extend(tick_events)
        self.log.metrics.append(metrics)
        self.log.tick = self.world.tick
        return metrics

    def run(self, ticks: int) -> tuple[TickMetrics, ...]:
        if ticks < 0:
            raise ValueError("ticks cannot be negative")
        metrics = tuple(self.step() for _ in range(ticks))
        self.world.verify_invariants()
        return metrics

    def verify_invariants(self) -> None:
        self.world.verify_invariants()

    def _validate_numerical_transition(
        self, actions: Mapping[AgentId, Action]
    ) -> None:
        positions = {
            agent_id: agent.position
            for agent_id, agent in self.world.agents.items()
            if agent.alive
        }
        for agent_id, action in actions.items():
            if action.kind is not ActionKind.MOVE:
                continue
            assert action.direction is not None
            current = positions[agent_id]
            dx, dy = action.direction.delta
            destination = (current[0] + dx, current[1] + dy)
            if self.world.in_bounds(destination):
                positions[agent_id] = destination

        inventories = {
            agent_id: {
                "food": agent.food_inventory,
                "water": agent.water_inventory,
            }
            for agent_id, agent in self.world.agents.items()
            if agent.alive
        }
        stocks: dict[tuple[int, int, str], float] = {}
        groups: dict[tuple[int, int, str], list[AgentId]] = {}
        for agent_id, action in sorted(actions.items()):
            if action.kind is not ActionKind.HARVEST:
                continue
            assert action.resource is not None
            x, y = positions[agent_id]
            key = (x, y, action.resource.value)
            groups.setdefault(key, []).append(agent_id)
            stocks[key] = self.world.cells[(x, y)].resource(action.resource).stock

        resolution_state = self._resolution_rng.state()
        try:
            for group_key in sorted(groups):
                harvesters = groups[group_key]
                resource_name = group_key[2]
                requested = {
                    agent_id: self._finite_product(
                        self.config.base_harvest_amount,
                        self.world.agents[agent_id].productivity(
                            actions[agent_id].resource  # type: ignore[arg-type]
                        ),
                    )
                    for agent_id in harvesters
                }
                total_requested = 0.0
                for amount in requested.values():
                    total_requested = self._finite_sum(total_requested, amount)
                if 0 < stocks[group_key] < total_requested:
                    self._resolution_rng.shuffle(harvesters)
                for agent_id in harvesters:
                    actual = min(requested[agent_id], stocks[group_key])
                    inventories[agent_id][resource_name] = self._finite_sum(
                        inventories[agent_id][resource_name], actual
                    )
                    stocks[group_key] -= actual
        finally:
            self._resolution_rng.restore(resolution_state)

        config = self.config
        for agent_id, agent in self.world.agents.items():
            if not agent.alive:
                continue
            food_consumed = min(inventories[agent_id]["food"], config.food_need)
            water_consumed = min(
                inventories[agent_id]["water"], config.water_need
            )
            food_deficit = config.food_need - food_consumed
            water_deficit = config.water_need - water_consumed
            food_loss = self._finite_product(
                food_deficit, config.food_health_penalty
            )
            water_loss = self._finite_product(
                water_deficit, config.water_health_penalty
            )
            self._finite_sum(food_loss, water_loss)

        for (x, y), cell in self.world.cells.items():
            for resource_name, resource in (
                ("food", cell.food),
                ("water", cell.water),
            ):
                stock = stocks.get((x, y, resource_name), resource.stock)
                self._finite_sum(stock, resource.regeneration_rate)

    def _resolve_movement(
        self, actions: Mapping[AgentId, Action], events: list[WorldEvent]
    ) -> None:
        for agent_id in sorted(actions):
            action = actions[agent_id]
            if action.kind is not ActionKind.MOVE:
                continue
            assert action.direction is not None
            agent = self.world.agents[agent_id]
            dx, dy = action.direction.delta
            destination = (agent.position[0] + dx, agent.position[1] + dy)
            if self.world.in_bounds(destination):
                agent.position = destination
            else:
                events.append(
                    InvalidActionEvent(
                        tick=self.world.tick,
                        agent_id=agent_id,
                        action=action,
                        reason="movement outside world boundary",
                    )
                )

    def _resolve_harvesting(
        self, actions: Mapping[AgentId, Action], events: list[WorldEvent]
    ) -> None:
        groups: dict[tuple[int, int, str], list[AgentId]] = {}
        for agent_id, action in sorted(actions.items()):
            if action.kind is not ActionKind.HARVEST:
                continue
            assert action.resource is not None
            x, y = self.world.agents[agent_id].position
            groups.setdefault((x, y, action.resource.value), []).append(agent_id)

        for group_key in sorted(groups):
            harvesters = groups[group_key]
            first_action = actions[harvesters[0]]
            assert first_action.resource is not None
            resource = first_action.resource
            position = (group_key[0], group_key[1])
            resource_state = self.world.cells[position].resource(resource)
            requested = {
                agent_id: self._finite_product(
                    self.config.base_harvest_amount,
                    self.world.agents[agent_id].productivity(resource),
                )
                for agent_id in harvesters
            }
            total_requested = 0.0
            for amount in requested.values():
                total_requested = self._finite_sum(total_requested, amount)
            if 0 < resource_state.stock < total_requested:
                self._resolution_rng.shuffle(harvesters)

            for agent_id in harvesters:
                actual = min(requested[agent_id], resource_state.stock)
                new_inventory = self._finite_sum(
                    self.world.agents[agent_id].inventory(resource), actual
                )
                resource_state.stock -= actual
                inventory_change = (
                    new_inventory
                    - self.world.agents[agent_id].inventory(resource)
                )
                self.world.agents[agent_id].add_inventory(
                    resource, inventory_change
                )
                events.append(
                    HarvestEvent(
                        tick=self.world.tick,
                        agent_id=agent_id,
                        resource=resource,
                        amount=actual,
                        position=position,
                    )
                )

    def _apply_metabolism(self, events: list[WorldEvent]) -> None:
        config = self.config
        for agent in self.world.living_agents():
            food_consumed = min(agent.food_inventory, config.food_need)
            water_consumed = min(agent.water_inventory, config.water_need)
            agent.food_inventory -= food_consumed
            agent.water_inventory -= water_consumed
            food_deficit = config.food_need - food_consumed
            water_deficit = config.water_need - water_consumed
            food_loss = self._finite_product(
                food_deficit, config.food_health_penalty
            )
            water_loss = self._finite_product(
                water_deficit, config.water_health_penalty
            )
            health_loss = self._finite_sum(food_loss, water_loss)
            agent.health = max(0.0, agent.health - health_loss)
            if not agent.alive:
                events.append(DeathEvent(self.world.tick, agent.id))

    def _regenerate_resources(self) -> None:
        for cell in self.world.cells.values():
            for resource in (cell.food, cell.water):
                regenerated = self._finite_sum(
                    resource.stock, resource.regeneration_rate
                )
                resource.stock = min(
                    resource.capacity,
                    regenerated,
                )

    @staticmethod
    def _finite_product(left: float, right: float) -> float:
        result = left * right
        if not isfinite(result):
            raise SimulationNumericalError(
                "transition arithmetic produced a non-finite product"
            )
        return result

    @staticmethod
    def _finite_sum(left: float, right: float) -> float:
        result = left + right
        if not isfinite(result):
            raise SimulationNumericalError(
                "transition arithmetic produced a non-finite sum"
            )
        return result

    def world_state_hash(self) -> str:
        """Return a stable hash of every scientific world-state field."""
        return self._hash_payload(self._world_state_payload())

    def state_hash(self) -> str:
        """Backward-compatible name for :meth:`world_state_hash`."""
        return self.world_state_hash()

    def execution_state_hash(self) -> str:
        """Hash every state component required for deterministic continuation."""
        return self._hash_payload(
            {
                "world": self._world_state_payload(),
                "configuration": self._canonicalize(self.config.as_dict()),
                "rng": {
                    "initialization": {
                        "seed": self._initialization_rng.seed,
                        "state": self._canonicalize(
                            self._initialization_rng.state()
                        ),
                    },
                    "policy": {
                        agent_id: {
                            "seed": rng.seed,
                            "state": self._canonicalize(rng.state()),
                        }
                        for agent_id, rng in sorted(self.policy_rngs.items())
                    },
                    "resolution": {
                        "seed": self._resolution_rng.seed,
                        "state": self._canonicalize(
                            self._resolution_rng.state()
                        ),
                    },
                },
                "policies": {
                    agent_id: {
                        "identity": self._policy_identity(policy),
                        "configuration": self._canonicalize(
                            policy.configuration_state()
                        ),
                        "continuation": self._canonicalize(
                            policy.continuation_state()
                        ),
                    }
                    for agent_id, policy in sorted(self.policies.items())
                },
                "agent_policy_state": {
                    agent_id: self._canonicalize(agent.policy_state)
                    for agent_id, agent in sorted(self.world.agents.items())
                },
            }
        )

    def _world_state_payload(self) -> dict[str, JsonValue]:
        cells = [
            [
                x,
                y,
                cell.food.stock,
                cell.food.capacity,
                cell.food.regeneration_rate,
                cell.water.stock,
                cell.water.capacity,
                cell.water.regeneration_rate,
            ]
            for (x, y), cell in sorted(self.world.cells.items())
        ]
        agents = [
            [
                agent.id,
                *agent.position,
                agent.food_inventory,
                agent.water_inventory,
                agent.health,
                agent.food_productivity,
                agent.water_productivity,
            ]
            for _, agent in sorted(self.world.agents.items())
        ]
        return {
            "tick": self.world.tick,
            "width": self.world.width,
            "height": self.world.height,
            "cells": cells,
            "agents": agents,
        }

    @staticmethod
    def _hash_payload(payload: JsonValue) -> str:
        encoded = json.dumps(
            payload,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _policy_identity(policy: Policy) -> str:
        policy_type = type(policy)
        return f"{policy_type.__module__}.{policy_type.__qualname__}"

    @classmethod
    def _canonicalize(cls, value: object) -> JsonValue:
        if isinstance(value, Enum):
            enum_type = type(value)
            return {
                "enum": f"{enum_type.__module__}.{enum_type.__qualname__}",
                "value": cls._canonicalize(value.value),
            }
        if value is None or type(value) in {bool, int, str}:
            return value
        if type(value) is float:
            if not isfinite(value):
                raise TypeError("execution state cannot contain non-finite floats")
            return value
        if type(value) is dict:
            items = [
                {
                    "key": cls._canonicalize(key),
                    "value": cls._canonicalize(item),
                }
                for key, item in value.items()
            ]
            items.sort(key=cls._canonical_sort_key)
            return {
                "container_type": cls._type_identity(type(value)),
                "items": items,
            }
        if type(value) in {list, tuple}:
            return {
                "container_type": cls._type_identity(type(value)),
                "items": [cls._canonicalize(item) for item in value],
            }
        if type(value) in {set, frozenset}:
            items = [cls._canonicalize(item) for item in value]
            items.sort(key=cls._canonical_sort_key)
            return {
                "container_type": cls._type_identity(type(value)),
                "items": items,
            }

        raise TypeError(
            "policy state contains unsupported canonical value "
            f"{type(value)!r}"
        )

    @staticmethod
    def _type_identity(value_type: type[object]) -> str:
        return f"{value_type.__module__}.{value_type.__qualname__}"

    @staticmethod
    def _canonical_sort_key(value: JsonValue) -> str:
        return json.dumps(
            value,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
