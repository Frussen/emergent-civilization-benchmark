"""M0 run configuration and baseline calibration defaults."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    width: int = 64
    height: int = 64
    initial_population: int = 256
    food_capacity: float = 20.0
    food_initial_stock: float = 20.0
    food_regeneration_rate: float = 1.0
    water_capacity: float = 20.0
    water_initial_stock: float = 20.0
    water_regeneration_rate: float = 1.0
    initial_health: float = 100.0
    initial_food_inventory: float = 20.0
    initial_water_inventory: float = 20.0
    food_productivity: float = 2.0
    water_productivity: float = 2.0
    food_need: float = 1.0
    water_need: float = 1.0
    food_health_penalty: float = 1.0
    water_health_penalty: float = 1.0
    base_harvest_amount: float = 1.0
    observation_radius: int = 3

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("world dimensions must be positive")
        if self.initial_population < 0:
            raise ValueError("initial population cannot be negative")
        if self.observation_radius < 0:
            raise ValueError("observation radius cannot be negative")

        values = asdict(self)
        float_values = (
            value for value in values.values() if isinstance(value, float)
        )
        if not all(isfinite(value) for value in float_values):
            raise ValueError("configuration values must be finite")
        nonnegative = (
            self.food_capacity,
            self.food_initial_stock,
            self.food_regeneration_rate,
            self.water_capacity,
            self.water_initial_stock,
            self.water_regeneration_rate,
            self.initial_food_inventory,
            self.initial_water_inventory,
            self.food_need,
            self.water_need,
            self.food_health_penalty,
            self.water_health_penalty,
            self.base_harvest_amount,
        )
        if any(value < 0 for value in nonnegative):
            raise ValueError("resource and metabolic parameters cannot be negative")
        if self.food_initial_stock > self.food_capacity:
            raise ValueError("initial food stock cannot exceed capacity")
        if self.water_initial_stock > self.water_capacity:
            raise ValueError("initial water stock cannot exceed capacity")
        if not 0 <= self.initial_health <= 100:
            raise ValueError("initial health must be between zero and 100")
        if self.food_productivity <= 0 or self.water_productivity <= 0:
            raise ValueError("productivity must be positive")

    def as_dict(self) -> dict[str, int | float]:
        return asdict(self)
