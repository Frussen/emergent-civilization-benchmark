import pytest

from ecb import (
    Observation,
    OracleSurvivalPolicy,
    RandomPolicy,
    Resource,
    Simulation,
    SimulationConfig,
)
from ecb.model import ObservedCell
from ecb.rng import SeededRNG


def test_oracle_harvests_partial_target_stock_on_current_cell() -> None:
    observation = Observation(
        own_id="agent",
        position=(0, 0),
        health=100.0,
        food_inventory=0.0,
        water_inventory=20.0,
        food_productivity=2.0,
        water_productivity=2.0,
        cells=(ObservedCell((0, 0), food_stock=0.5, water_stock=20.0),),
        visible_agents=(),
    )
    action = OracleSurvivalPolicy().decide(observation, SeededRNG(0))
    assert action == action.harvest(Resource.FOOD)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_baseline_oracle_survival_at_2000_ticks(seed: int) -> None:
    config = SimulationConfig()
    simulation = Simulation(
        config,
        seed,
        policy_factory=lambda _id: OracleSurvivalPolicy(
            food_need=config.food_need,
            water_need=config.water_need,
            base_harvest_amount=config.base_harvest_amount,
        ),
    )
    metrics = simulation.run(2_000)[-1]
    assert metrics.survival_fraction >= 0.95


def test_random_policy_is_meaningfully_weaker_than_survival_control() -> None:
    config = SimulationConfig()
    random_run = Simulation(
        config, 0, policy_factory=lambda _id: RandomPolicy()
    ).run(200)[-1]
    oracle_run = Simulation(
        config,
        0,
        policy_factory=lambda _id: OracleSurvivalPolicy(),
    ).run(200)[-1]
    assert oracle_run.survival_fraction >= 0.95
    assert random_run.survival_fraction < oracle_run.survival_fraction
