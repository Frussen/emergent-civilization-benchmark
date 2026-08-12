"""Typed data structures for the framework-independent M0 world."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite

type AgentId = str
type Position = tuple[int, int]


class Resource(StrEnum):
    FOOD = "food"
    WATER = "water"


class Direction(StrEnum):
    NORTH = "north"
    NORTH_EAST = "north-east"
    EAST = "east"
    SOUTH_EAST = "south-east"
    SOUTH = "south"
    SOUTH_WEST = "south-west"
    WEST = "west"
    NORTH_WEST = "north-west"

    @property
    def delta(self) -> Position:
        return {
            Direction.NORTH: (0, -1),
            Direction.NORTH_EAST: (1, -1),
            Direction.EAST: (1, 0),
            Direction.SOUTH_EAST: (1, 1),
            Direction.SOUTH: (0, 1),
            Direction.SOUTH_WEST: (-1, 1),
            Direction.WEST: (-1, 0),
            Direction.NORTH_WEST: (-1, -1),
        }[self]


class ActionKind(StrEnum):
    WAIT = "wait"
    MOVE = "move"
    HARVEST = "harvest"


@dataclass(frozen=True, slots=True)
class Action:
    kind: ActionKind
    direction: Direction | None = None
    resource: Resource | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ActionKind):
            raise TypeError("kind must be an ActionKind")
        if self.direction is not None and not isinstance(self.direction, Direction):
            raise TypeError("direction must be a Direction")
        if self.resource is not None and not isinstance(self.resource, Resource):
            raise TypeError("resource must be a Resource")
        if self.kind is ActionKind.MOVE and self.direction is None:
            raise ValueError("MOVE requires a direction")
        if self.kind is ActionKind.HARVEST and self.resource is None:
            raise ValueError("HARVEST requires a resource")
        if self.kind is not ActionKind.MOVE and self.direction is not None:
            raise ValueError("only MOVE accepts a direction")
        if self.kind is not ActionKind.HARVEST and self.resource is not None:
            raise ValueError("only HARVEST accepts a resource")

    @classmethod
    def wait(cls) -> Action:
        return cls(ActionKind.WAIT)

    @classmethod
    def move(cls, direction: Direction) -> Action:
        return cls(ActionKind.MOVE, direction=direction)

    @classmethod
    def harvest(cls, resource: Resource) -> Action:
        return cls(ActionKind.HARVEST, resource=resource)


@dataclass(slots=True)
class ResourceState:
    stock: float
    capacity: float
    regeneration_rate: float


@dataclass(slots=True)
class CellState:
    food: ResourceState
    water: ResourceState

    def resource(self, resource: Resource) -> ResourceState:
        return self.food if resource is Resource.FOOD else self.water


@dataclass(slots=True)
class AgentState:
    id: AgentId
    position: Position
    food_inventory: float
    water_inventory: float
    health: float
    food_productivity: float
    water_productivity: float
    policy_state: tuple[tuple[str, str], ...] = ()

    def __setattr__(self, name: str, value: object) -> None:
        if name == "id" and hasattr(self, "id"):
            raise AttributeError("agent ID is immutable")
        object.__setattr__(self, name, value)

    @property
    def alive(self) -> bool:
        return self.health > 0.0

    def inventory(self, resource: Resource) -> float:
        return (
            self.food_inventory
            if resource is Resource.FOOD
            else self.water_inventory
        )

    def add_inventory(self, resource: Resource, amount: float) -> None:
        if resource is Resource.FOOD:
            self.food_inventory += amount
        else:
            self.water_inventory += amount

    def productivity(self, resource: Resource) -> float:
        return (
            self.food_productivity
            if resource is Resource.FOOD
            else self.water_productivity
        )


@dataclass(slots=True)
class WorldState:
    width: int
    height: int
    cells: dict[Position, CellState]
    agents: dict[AgentId, AgentState]
    tick: int = 0

    def in_bounds(self, position: Position) -> bool:
        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height

    def living_agents(self) -> tuple[AgentState, ...]:
        return tuple(
            agent for _, agent in sorted(self.agents.items()) if agent.alive
        )

    def agents_at(self, position: Position) -> tuple[AgentState, ...]:
        return tuple(
            agent
            for agent in self.living_agents()
            if agent.position == position
        )

    def verify_invariants(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise AssertionError("world dimensions must be positive")
        expected = {
            (x, y) for x in range(self.width) for y in range(self.height)
        }
        if set(self.cells) != expected:
            raise AssertionError("world must contain exactly one state per cell")
        if self.tick < 0:
            raise AssertionError("tick cannot be negative")

        for cell in self.cells.values():
            for resource in (cell.food, cell.water):
                values = (
                    resource.stock,
                    resource.capacity,
                    resource.regeneration_rate,
                )
                if not all(isfinite(value) for value in values):
                    raise AssertionError("resource values must be finite")
                if resource.capacity < 0 or resource.regeneration_rate < 0:
                    raise AssertionError("resource parameters cannot be negative")
                if not 0 <= resource.stock <= resource.capacity:
                    raise AssertionError("resource stock must be within capacity")

        for key, agent in self.agents.items():
            if key != agent.id:
                raise AssertionError("agent dictionary key must equal immutable ID")
            if not self.in_bounds(agent.position):
                raise AssertionError("agent position must be in bounds")
            values = (
                agent.food_inventory,
                agent.water_inventory,
                agent.health,
                agent.food_productivity,
                agent.water_productivity,
            )
            if not all(isfinite(value) for value in values):
                raise AssertionError("agent values must be finite")
            if agent.food_inventory < 0 or agent.water_inventory < 0:
                raise AssertionError("inventories cannot be negative")
            if not 0 <= agent.health <= 100:
                raise AssertionError("health must be between zero and 100")
            if agent.food_productivity <= 0 or agent.water_productivity <= 0:
                raise AssertionError("productivity must be positive")


@dataclass(frozen=True, slots=True)
class VisibleAgent:
    id: AgentId
    relative_position: Position


@dataclass(frozen=True, slots=True)
class ObservedCell:
    relative_position: Position
    food_stock: float
    water_stock: float

    def stock(self, resource: Resource) -> float:
        return self.food_stock if resource is Resource.FOOD else self.water_stock


@dataclass(frozen=True, slots=True)
class Observation:
    own_id: AgentId
    position: Position
    health: float
    food_inventory: float
    water_inventory: float
    food_productivity: float
    water_productivity: float
    cells: tuple[ObservedCell, ...]
    visible_agents: tuple[VisibleAgent, ...]

    def inventory(self, resource: Resource) -> float:
        return (
            self.food_inventory
            if resource is Resource.FOOD
            else self.water_inventory
        )

    def productivity(self, resource: Resource) -> float:
        return (
            self.food_productivity
            if resource is Resource.FOOD
            else self.water_productivity
        )

    def current_cell(self) -> ObservedCell:
        return next(cell for cell in self.cells if cell.relative_position == (0, 0))


@dataclass(frozen=True, slots=True)
class InvalidActionEvent:
    tick: int
    agent_id: AgentId
    action: Action
    reason: str


@dataclass(frozen=True, slots=True)
class HarvestEvent:
    tick: int
    agent_id: AgentId
    resource: Resource
    amount: float
    position: Position


@dataclass(frozen=True, slots=True)
class DeathEvent:
    tick: int
    agent_id: AgentId


type WorldEvent = InvalidActionEvent | HarvestEvent | DeathEvent


@dataclass(frozen=True, slots=True)
class TickMetrics:
    tick: int
    living_population: int
    survival_fraction: float


@dataclass(slots=True)
class RunLog:
    seed: int
    configuration: dict[str, int | float]
    software_version: str
    initial_agent_ids: tuple[AgentId, ...]
    policy_identities: dict[AgentId, str]
    policy_configurations: dict[AgentId, object]
    tick: int = 0
    actions: list[tuple[int, AgentId, Action]] = field(default_factory=list)
    events: list[WorldEvent] = field(default_factory=list)
    metrics: list[TickMetrics] = field(default_factory=list)


class SimulationNumericalError(RuntimeError):
    """Raised when a transition would create non-finite scientific state."""
