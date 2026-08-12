from dataclasses import FrozenInstanceError

import pytest

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


def test_observation_uses_chebyshev_radius_and_clips_boundaries() -> None:
    simulation = Simulation(
        SimulationConfig(
            width=6, height=5, initial_population=2, observation_radius=2
        ),
        0,
        agent_ids=("observer", "hidden"),
    )
    simulation.world.agents["observer"].position = (0, 0)
    simulation.world.agents["hidden"].position = (3, 0)

    observation = simulation.observe("observer")

    assert len(observation.cells) == 9
    assert {(cell.relative_position) for cell in observation.cells} == {
        (x, y) for x in range(3) for y in range(3)
    }
    assert observation.visible_agents == ()


def test_observation_hides_world_and_other_agent_state() -> None:
    simulation = Simulation(
        SimulationConfig(width=2, height=1, initial_population=2),
        0,
        agent_ids=("a", "b"),
    )
    simulation.world.agents["a"].position = (0, 0)
    simulation.world.agents["b"].position = (1, 0)
    simulation.world.agents["b"].policy_state = (("secret", "value"),)
    observation = simulation.observe("a")

    assert not hasattr(observation, "world")
    assert not hasattr(observation.cells[0], "capacity")
    visible_b = next(agent for agent in observation.visible_agents if agent.id == "b")
    assert set(visible_b.__slots__) == {"id", "relative_position"}
    with pytest.raises(FrozenInstanceError):
        observation.health = 0  # type: ignore[misc]


def test_observation_hides_clock_and_canonically_orders_visible_agents() -> None:
    simulation = Simulation(
        SimulationConfig(width=3, height=3, initial_population=4),
        0,
        agent_ids=("observer", "z", "a", "middle"),
    )
    simulation.world.agents["observer"].position = (1, 1)
    simulation.world.agents["z"].position = (0, 1)
    simulation.world.agents["a"].position = (0, 1)
    simulation.world.agents["middle"].position = (1, 0)
    observation = simulation.observe("observer")

    assert not hasattr(observation, "tick")
    assert tuple(agent.id for agent in observation.visible_agents) == (
        "a",
        "z",
        "middle",
    )
