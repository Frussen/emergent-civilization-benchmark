"""M0 agent policies, separate from all world mechanics."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Protocol

from ecb.model import Action, Direction, Observation, Resource
from ecb.rng import SeededRNG

type CanonicalPolicyState = (
    None
    | bool
    | int
    | float
    | str
    | Resource
    | Direction
    | list["CanonicalPolicyState"]
    | tuple["CanonicalPolicyState", ...]
    | set["CanonicalPolicyState"]
    | frozenset["CanonicalPolicyState"]
    | dict["CanonicalPolicyState", "CanonicalPolicyState"]
)


class Policy(Protocol):
    def decide(self, observation: Observation, rng: SeededRNG) -> Action: ...

    def configuration_state(self) -> CanonicalPolicyState: ...

    def continuation_state(self) -> CanonicalPolicyState: ...


class RandomPolicy:
    """Choose uniformly from the complete M0 action vocabulary."""

    _actions = (
        Action.wait(),
        *(Action.move(direction) for direction in Direction),
        Action.harvest(Resource.FOOD),
        Action.harvest(Resource.WATER),
    )

    def decide(self, observation: Observation, rng: SeededRNG) -> Action:
        del observation
        return rng.choice(self._actions)

    def configuration_state(self) -> CanonicalPolicyState:
        return None

    def continuation_state(self) -> CanonicalPolicyState:
        return None


@dataclass(frozen=True, slots=True)
class OracleSurvivalPolicy:
    """Observation-only control policy specified for M0 viability testing."""

    food_need: float = 1.0
    water_need: float = 1.0
    base_harvest_amount: float = 1.0

    def decide(self, observation: Observation, rng: SeededRNG) -> Action:
        del rng
        food_time = self._survival_time(
            observation.food_inventory, self.food_need
        )
        water_time = self._survival_time(
            observation.water_inventory, self.water_need
        )
        target = Resource.FOOD if food_time <= water_time else Resource.WATER

        full_harvest = (
            self.base_harvest_amount * observation.productivity(target)
        )
        if observation.current_cell().stock(target) >= full_harvest:
            return Action.harvest(target)

        candidates = [cell for cell in observation.cells if cell.stock(target) > 0]
        if not candidates:
            return Action.wait()
        greatest_stock = max(cell.stock(target) for cell in candidates)
        richest = [
            cell for cell in candidates if cell.stock(target) == greatest_stock
        ]
        richest.sort(
            key=lambda cell: (
                max(abs(cell.relative_position[0]), abs(cell.relative_position[1])),
                observation.position[0] + cell.relative_position[0],
                observation.position[1] + cell.relative_position[1],
            )
        )
        dx, dy = richest[0].relative_position
        if (dx, dy) == (0, 0):
            return Action.harvest(target)
        direction_by_delta = {direction.delta: direction for direction in Direction}
        step = (self._sign(dx), self._sign(dy))
        return Action.move(direction_by_delta[step])

    @staticmethod
    def _survival_time(inventory: float, need: float) -> float:
        return inventory / need if need > 0 else inf

    @staticmethod
    def _sign(value: int) -> int:
        return (value > 0) - (value < 0)

    def configuration_state(self) -> CanonicalPolicyState:
        return {
            "food_need": self.food_need,
            "water_need": self.water_need,
            "base_harvest_amount": self.base_harvest_amount,
        }

    def continuation_state(self) -> CanonicalPolicyState:
        return None
