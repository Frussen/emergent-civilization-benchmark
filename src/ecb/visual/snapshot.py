"""Immutable observational projection of an authoritative simulation state."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from ecb.model import DeathEvent, HarvestEvent, InvalidActionEvent
from ecb.simulation import Simulation

RECENT_EVENT_LIMIT = 75

type JsonValue = (
    None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
)


def _require_json_number(value: object, field_name: str) -> None:
    if type(value) not in {int, float}:
        raise TypeError(f"{field_name} must be a built-in int or float")
    if type(value) is float and not isfinite(value):
        raise ValueError(f"{field_name} must be finite")


@dataclass(frozen=True, slots=True)
class VisualWorld:
    """World geometry using ECB's canonical ``(x, y)`` coordinates."""

    width: int
    height: int

    def __post_init__(self) -> None:
        if type(self.width) is not int or type(self.height) is not int:
            raise TypeError("visual world dimensions must be integers")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("visual world dimensions must be positive")


@dataclass(frozen=True, slots=True)
class VisualAgent:
    """Detached physical state for one agent, living or dead."""

    id: str
    x: int
    y: int
    alive: bool
    health: int | float
    food_inventory: int | float
    water_inventory: int | float

    def __post_init__(self) -> None:
        if type(self.id) is not str:
            raise TypeError("visual agent ID must be a string")
        if type(self.x) is not int or type(self.y) is not int:
            raise TypeError("visual agent coordinates must be integers")
        if type(self.alive) is not bool:
            raise TypeError("visual agent alive state must be a boolean")
        _require_json_number(self.health, "agent health")
        _require_json_number(self.food_inventory, "agent food inventory")
        _require_json_number(self.water_inventory, "agent water inventory")


@dataclass(frozen=True, slots=True)
class VisualCell:
    """Detached resource stocks for one canonical world coordinate."""

    x: int
    y: int
    food_stock: int | float
    food_capacity: int | float
    water_stock: int | float
    water_capacity: int | float

    def __post_init__(self) -> None:
        if type(self.x) is not int or type(self.y) is not int:
            raise TypeError("visual cell coordinates must be integers")
        _require_json_number(self.food_stock, "cell food stock")
        _require_json_number(self.food_capacity, "cell food capacity")
        _require_json_number(self.water_stock, "cell water stock")
        _require_json_number(self.water_capacity, "cell water capacity")
        if self.food_capacity < 0 or self.water_capacity < 0:
            raise ValueError("visual cell capacities cannot be negative")
        if not 0 <= self.food_stock <= self.food_capacity:
            raise ValueError("visual cell food stock must be within capacity")
        if not 0 <= self.water_stock <= self.water_capacity:
            raise ValueError("visual cell water stock must be within capacity")


@dataclass(frozen=True, slots=True)
class VisualHarvestEvent:
    tick: int
    agent_id: str
    resource: str
    amount: int | float
    x: int
    y: int

    def __post_init__(self) -> None:
        _validate_event_identity(self.tick, self.agent_id)
        if self.resource not in {"food", "water"}:
            raise ValueError("visual harvest resource must be food or water")
        _require_json_number(self.amount, "visual harvest amount")
        if self.amount < 0:
            raise ValueError("visual harvest amount cannot be negative")
        _validate_event_coordinates(self.x, self.y)


@dataclass(frozen=True, slots=True)
class VisualDeathEvent:
    tick: int
    agent_id: str

    def __post_init__(self) -> None:
        _validate_event_identity(self.tick, self.agent_id)


@dataclass(frozen=True, slots=True)
class VisualInvalidActionEvent:
    tick: int
    agent_id: str
    action_kind: str
    direction: str | None
    resource: str | None
    reason: str

    def __post_init__(self) -> None:
        _validate_event_identity(self.tick, self.agent_id)
        if self.action_kind not in {"wait", "move", "harvest"}:
            raise ValueError("unsupported visual action kind")
        directions = {
            "north",
            "north-east",
            "east",
            "south-east",
            "south",
            "south-west",
            "west",
            "north-west",
        }
        if self.direction is not None and self.direction not in directions:
            raise ValueError("unsupported visual event direction")
        if self.resource is not None and self.resource not in {"food", "water"}:
            raise ValueError("visual event resource must be food, water, or None")
        if self.action_kind == "move" and self.direction is None:
            raise ValueError("visual MOVE requires a direction")
        if self.action_kind == "harvest" and self.resource is None:
            raise ValueError("visual HARVEST requires a resource")
        if self.action_kind != "move" and self.direction is not None:
            raise ValueError("only visual MOVE accepts a direction")
        if self.action_kind != "harvest" and self.resource is not None:
            raise ValueError("only visual HARVEST accepts a resource")
        if type(self.reason) is not str:
            raise TypeError("visual invalid-action reason must be a string")


type VisualEvent = VisualHarvestEvent | VisualDeathEvent | VisualInvalidActionEvent


def _validate_event_identity(tick: object, agent_id: object) -> None:
    if type(tick) is not int or tick < 0:
        raise ValueError("visual event tick must be a nonnegative integer")
    if type(agent_id) is not str:
        raise TypeError("visual event agent ID must be a string")


def _validate_event_coordinates(x: object, y: object) -> None:
    if type(x) is not int or type(y) is not int:
        raise TypeError("visual event coordinates must be integers")


@dataclass(frozen=True, slots=True)
class VisualMetrics:
    """Lightweight metrics with the same semantics as the headless runner."""

    alive_agents: int
    mean_health_alive: int | float | None
    total_world_food: int | float
    total_world_water: int | float

    def __post_init__(self) -> None:
        if type(self.alive_agents) is not int:
            raise TypeError("alive agent count must be an integer")
        if self.alive_agents < 0:
            raise ValueError("alive agent count cannot be negative")
        if self.mean_health_alive is not None:
            _require_json_number(self.mean_health_alive, "mean health of living agents")
        _require_json_number(self.total_world_food, "total world food")
        _require_json_number(self.total_world_water, "total world water")


@dataclass(frozen=True, slots=True)
class VisualSnapshot:
    """Immutable, detached, deterministically ordered visual state."""

    tick: int
    world_state_hash: str
    health_reference: int | float
    world: VisualWorld
    agents: tuple[VisualAgent, ...]
    cells: tuple[VisualCell, ...]
    metrics: VisualMetrics
    recent_events: tuple[VisualEvent, ...]

    def __post_init__(self) -> None:
        if type(self.tick) is not int:
            raise TypeError("visual snapshot tick must be an integer")
        if self.tick < 0:
            raise ValueError("visual snapshot tick cannot be negative")
        if type(self.world_state_hash) is not str:
            raise TypeError("world state hash must be a string")
        _require_json_number(self.health_reference, "visual health reference")
        if self.health_reference < 0:
            raise ValueError("visual health reference cannot be negative")
        if type(self.world) is not VisualWorld:
            raise TypeError("world must be a VisualWorld")
        if type(self.agents) is not tuple or not all(
            type(agent) is VisualAgent for agent in self.agents
        ):
            raise TypeError("agents must be a tuple of VisualAgent values")
        if type(self.cells) is not tuple or not all(
            type(cell) is VisualCell for cell in self.cells
        ):
            raise TypeError("cells must be a tuple of VisualCell values")
        if type(self.metrics) is not VisualMetrics:
            raise TypeError("metrics must be VisualMetrics")
        event_types = (VisualHarvestEvent, VisualDeathEvent, VisualInvalidActionEvent)
        if type(self.recent_events) is not tuple or not all(
            type(event) in event_types for event in self.recent_events
        ):
            raise TypeError("recent events must be a tuple of visual event values")
        if len(self.recent_events) > RECENT_EVENT_LIMIT:
            raise ValueError("recent events exceed the visual tail limit")
        if tuple(event.tick for event in self.recent_events) != tuple(
            sorted(event.tick for event in self.recent_events)
        ):
            raise ValueError("recent events must retain chronological log order")

        agent_ids = tuple(agent.id for agent in self.agents)
        if len(set(agent_ids)) != len(agent_ids):
            raise ValueError("visual agent IDs must be unique")
        if agent_ids != tuple(sorted(agent_ids)):
            raise ValueError("visual agents must be ordered canonically by ID")
        if any(
            not (0 <= agent.x < self.world.width and 0 <= agent.y < self.world.height)
            for agent in self.agents
        ):
            raise ValueError("visual agent coordinates must be within world bounds")

        cell_coordinates = tuple((cell.x, cell.y) for cell in self.cells)
        if len(set(cell_coordinates)) != len(cell_coordinates):
            raise ValueError("visual cell coordinates must be unique")
        if cell_coordinates != tuple(sorted(cell_coordinates)):
            raise ValueError("visual cells must be ordered canonically by (x, y)")
        if any(
            not (0 <= cell.x < self.world.width and 0 <= cell.y < self.world.height)
            for cell in self.cells
        ):
            raise ValueError("visual cell coordinates must be within world bounds")
        if len(self.cells) != self.world.width * self.world.height:
            raise ValueError("visual cells must cover every world coordinate exactly")
        if any(
            type(event) is VisualHarvestEvent
            and not (
                0 <= event.x < self.world.width and 0 <= event.y < self.world.height
            )
            for event in self.recent_events
        ):
            raise ValueError("visual harvest event coordinates must be within bounds")

    @classmethod
    def from_simulation(cls, simulation: Simulation) -> VisualSnapshot:
        """Capture the current state without advancing or mutating ``simulation``.

        This operation is synchronous but not independently thread-safe. Callers
        must serialize snapshot capture and ``Simulation.step`` through one
        synchronization boundary; ``VisualRuntime`` supplies that boundary for
        the visual server.
        """
        world = simulation.world
        agents = tuple(
            VisualAgent(
                id=agent.id,
                x=agent.position[0],
                y=agent.position[1],
                alive=agent.alive,
                health=agent.health,
                food_inventory=agent.food_inventory,
                water_inventory=agent.water_inventory,
            )
            for _, agent in sorted(world.agents.items())
        )
        cells = tuple(
            VisualCell(
                x=x,
                y=y,
                food_stock=cell.food.stock,
                food_capacity=cell.food.capacity,
                water_stock=cell.water.stock,
                water_capacity=cell.water.capacity,
            )
            for (x, y), cell in sorted(world.cells.items())
        )
        living = tuple(agent for agent in agents if agent.alive)
        alive_agents = len(living)
        mean_health_alive = (
            sum(agent.health for agent in living) / alive_agents
            if alive_agents
            else None
        )
        recent_events = tuple(
            _visual_event(event)
            for event in simulation.log.events[-RECENT_EVENT_LIMIT:]
        )
        return cls(
            tick=world.tick,
            world_state_hash=simulation.world_state_hash(),
            health_reference=simulation.config.initial_health,
            world=VisualWorld(width=world.width, height=world.height),
            agents=agents,
            cells=cells,
            metrics=VisualMetrics(
                alive_agents=alive_agents,
                mean_health_alive=mean_health_alive,
                total_world_food=sum(cell.food_stock for cell in cells),
                total_world_water=sum(cell.water_stock for cell in cells),
            ),
            recent_events=recent_events,
        )

    def to_json_data(self) -> dict[str, JsonValue]:
        """Return the explicit VisualSnapshot schema as JSON-compatible data."""
        return {
            "tick": self.tick,
            "world_state_hash": self.world_state_hash,
            "health_reference": self.health_reference,
            "world": {
                "width": self.world.width,
                "height": self.world.height,
            },
            "agents": [
                {
                    "id": agent.id,
                    "x": agent.x,
                    "y": agent.y,
                    "alive": agent.alive,
                    "health": agent.health,
                    "food_inventory": agent.food_inventory,
                    "water_inventory": agent.water_inventory,
                }
                for agent in self.agents
            ],
            "cells": [
                {
                    "x": cell.x,
                    "y": cell.y,
                    "food_stock": cell.food_stock,
                    "food_capacity": cell.food_capacity,
                    "water_stock": cell.water_stock,
                    "water_capacity": cell.water_capacity,
                }
                for cell in self.cells
            ],
            "metrics": {
                "alive_agents": self.metrics.alive_agents,
                "mean_health_alive": self.metrics.mean_health_alive,
                "total_world_food": self.metrics.total_world_food,
                "total_world_water": self.metrics.total_world_water,
            },
            "recent_events": [
                _visual_event_json(event) for event in self.recent_events
            ],
        }


def _visual_event(
    event: InvalidActionEvent | HarvestEvent | DeathEvent,
) -> VisualEvent:
    if type(event) is HarvestEvent:
        return VisualHarvestEvent(
            tick=event.tick,
            agent_id=event.agent_id,
            resource=event.resource.value,
            amount=event.amount,
            x=event.position[0],
            y=event.position[1],
        )
    if type(event) is DeathEvent:
        return VisualDeathEvent(tick=event.tick, agent_id=event.agent_id)
    if type(event) is InvalidActionEvent:
        return VisualInvalidActionEvent(
            tick=event.tick,
            agent_id=event.agent_id,
            action_kind=event.action.kind.value,
            direction=(
                event.action.direction.value
                if event.action.direction is not None
                else None
            ),
            resource=(
                event.action.resource.value
                if event.action.resource is not None
                else None
            ),
            reason=event.reason,
        )
    raise TypeError(f"unsupported canonical event type: {type(event)!r}")


def _visual_event_json(event: VisualEvent) -> dict[str, JsonValue]:
    if type(event) is VisualHarvestEvent:
        return {
            "event_type": "harvest",
            "tick": event.tick,
            "agent_id": event.agent_id,
            "resource": event.resource,
            "amount": event.amount,
            "x": event.x,
            "y": event.y,
        }
    if type(event) is VisualDeathEvent:
        return {
            "event_type": "death",
            "tick": event.tick,
            "agent_id": event.agent_id,
        }
    return {
        "event_type": "invalid_action",
        "tick": event.tick,
        "agent_id": event.agent_id,
        "action_kind": event.action_kind,
        "direction": event.direction,
        "resource": event.resource,
        "reason": event.reason,
    }
