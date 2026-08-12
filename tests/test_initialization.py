from dataclasses import FrozenInstanceError

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ecb import RandomPolicy, SimulationConfig
from ecb import Simulation as EcbSimulation


def Simulation(
    config: SimulationConfig,
    seed: int = 0,
    *,
    agent_ids: tuple[str, ...] | None = None,
) -> EcbSimulation:
    return EcbSimulation(
        config,
        seed,
        policy_factory=lambda _id: RandomPolicy(),
        agent_ids=agent_ids,
    )


def test_policy_assignment_is_explicit() -> None:
    with pytest.raises(ValueError, match="must be supplied explicitly"):
        EcbSimulation(SimulationConfig(initial_population=1), seed=0)


def test_baseline_defaults_match_model_spec() -> None:
    config = SimulationConfig()
    simulation = Simulation(config, seed=7)

    assert (simulation.world.width, simulation.world.height) == (64, 64)
    assert len(simulation.world.agents) == 256
    assert all(
        (cell.food.stock, cell.food.capacity, cell.food.regeneration_rate)
        == (20.0, 20.0, 1.0)
        for cell in simulation.world.cells.values()
    )
    assert all(
        (cell.water.stock, cell.water.capacity, cell.water.regeneration_rate)
        == (20.0, 20.0, 1.0)
        for cell in simulation.world.cells.values()
    )
    assert all(
        (
            agent.health,
            agent.food_inventory,
            agent.water_inventory,
            agent.food_productivity,
            agent.water_productivity,
        )
        == (100.0, 20.0, 20.0, 2.0, 2.0)
        for agent in simulation.world.agents.values()
    )


def test_initial_placement_allows_multi_agent_occupancy() -> None:
    simulation = Simulation(
        SimulationConfig(width=1, height=1, initial_population=4), seed=3
    )
    assert len(simulation.world.agents_at((0, 0))) == 4


def test_agent_input_order_does_not_change_initialization() -> None:
    config = SimulationConfig(width=5, height=4, initial_population=3)
    ids = ("z", "a", "m")
    first = Simulation(config, seed=4, agent_ids=ids)
    second = Simulation(config, seed=4, agent_ids=tuple(reversed(ids)))

    assert {
        agent_id: agent.position for agent_id, agent in first.world.agents.items()
    } == {
        agent_id: agent.position for agent_id, agent in second.world.agents.items()
    }


def test_explicit_empty_agent_ids_must_match_population_count() -> None:
    config = SimulationConfig(initial_population=1)
    with pytest.raises(ValueError, match="count must match"):
        Simulation(config, seed=0, agent_ids=())


@given(
    width=st.integers(min_value=1, max_value=8),
    height=st.integers(min_value=1, max_value=8),
    population=st.integers(min_value=0, max_value=30),
    seed=st.integers(),
)
def test_seeded_initial_positions_are_in_configurable_world(
    width: int, height: int, population: int, seed: int
) -> None:
    simulation = Simulation(
        SimulationConfig(
            width=width, height=height, initial_population=population
        ),
        seed,
    )
    assert all(
        0 <= agent.position[0] < width and 0 <= agent.position[1] < height
        for agent in simulation.world.agents.values()
    )


def test_configuration_is_immutable() -> None:
    config = SimulationConfig()
    with pytest.raises(FrozenInstanceError):
        config.width = 3  # type: ignore[misc]


def test_agent_ids_are_immutable() -> None:
    simulation = Simulation(SimulationConfig(initial_population=1), seed=0)
    agent = next(iter(simulation.world.agents.values()))
    with pytest.raises(AttributeError, match="immutable"):
        agent.id = "replacement"
