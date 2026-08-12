"""Immutable observational projection of an authoritative simulation state."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from ecb.simulation import Simulation

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
    water_stock: int | float

    def __post_init__(self) -> None:
        if type(self.x) is not int or type(self.y) is not int:
            raise TypeError("visual cell coordinates must be integers")
        _require_json_number(self.food_stock, "cell food stock")
        _require_json_number(self.water_stock, "cell water stock")


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
    world: VisualWorld
    agents: tuple[VisualAgent, ...]
    cells: tuple[VisualCell, ...]
    metrics: VisualMetrics

    def __post_init__(self) -> None:
        if type(self.tick) is not int:
            raise TypeError("visual snapshot tick must be an integer")
        if self.tick < 0:
            raise ValueError("visual snapshot tick cannot be negative")
        if type(self.world_state_hash) is not str:
            raise TypeError("world state hash must be a string")
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
                water_stock=cell.water.stock,
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
        return cls(
            tick=world.tick,
            world_state_hash=simulation.world_state_hash(),
            world=VisualWorld(width=world.width, height=world.height),
            agents=agents,
            cells=cells,
            metrics=VisualMetrics(
                alive_agents=alive_agents,
                mean_health_alive=mean_health_alive,
                total_world_food=sum(cell.food_stock for cell in cells),
                total_world_water=sum(cell.water_stock for cell in cells),
            ),
        )

    def to_json_data(self) -> dict[str, JsonValue]:
        """Return the explicit VisualSnapshot schema as JSON-compatible data."""
        return {
            "tick": self.tick,
            "world_state_hash": self.world_state_hash,
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
                    "water_stock": cell.water_stock,
                }
                for cell in self.cells
            ],
            "metrics": {
                "alive_agents": self.metrics.alive_agents,
                "mean_health_alive": self.metrics.mean_health_alive,
                "total_world_food": self.metrics.total_world_food,
                "total_world_water": self.metrics.total_world_water,
            },
        }
