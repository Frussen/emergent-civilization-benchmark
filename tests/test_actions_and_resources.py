import sys
from collections import Counter

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ecb import (
    Action,
    ActionKind,
    Direction,
    Resource,
    SimulationConfig,
    SimulationNumericalError,
)
from ecb import (
    Simulation as EcbSimulation,
)
from ecb.model import HarvestEvent, InvalidActionEvent
from ecb.policies import RandomPolicy


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


def zero_metabolism_config(**changes: int | float) -> SimulationConfig:
    values: dict[str, int | float] = {
        "width": 3,
        "height": 3,
        "initial_population": 1,
        "food_need": 0.0,
        "water_need": 0.0,
    }
    values.update(changes)
    return SimulationConfig(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("action", "message"),
    [
        (lambda: Action("wait"), "kind must be an ActionKind"),
        (
            lambda: Action(ActionKind.MOVE, direction="east"),
            "direction must be a Direction",
        ),
        (
            lambda: Action(ActionKind.HARVEST, resource="food"),
            "resource must be a Resource",
        ),
        (lambda: Action.move("east"), "direction must be a Direction"),
        (lambda: Action.harvest("food"), "resource must be a Resource"),
    ],
)
def test_action_rejects_raw_strings_for_enum_fields(
    action: object, message: str
) -> None:
    with pytest.raises(TypeError, match=message):
        action()  # type: ignore[operator]


def test_wait_only_allows_metabolism_and_regeneration() -> None:
    simulation = Simulation(SimulationConfig(initial_population=1), seed=0)
    agent = next(iter(simulation.world.agents.values()))
    cell = simulation.world.cells[agent.position]
    cell.food.stock = 0.0
    simulation.step({agent.id: Action.wait()})

    assert agent.food_inventory == 19.0
    assert agent.water_inventory == 19.0
    assert cell.food.stock == 1.0


@given(stock=st.floats(min_value=0, max_value=20, allow_nan=False))
def test_harvest_conserves_resource_exactly(stock: float) -> None:
    simulation = Simulation(zero_metabolism_config(), seed=0)
    agent = next(iter(simulation.world.agents.values()))
    cell = simulation.world.cells[agent.position]
    cell.food.stock = stock
    cell.food.regeneration_rate = 0.0
    before_total = cell.food.stock + agent.food_inventory

    simulation.step({agent.id: Action.harvest(Resource.FOOD)})

    simulation.verify_invariants()
    assert cell.food.stock + agent.food_inventory == before_total
    assert cell.food.stock >= 0
    assert agent.food_inventory >= 0


def test_regeneration_respects_capacity() -> None:
    simulation = Simulation(zero_metabolism_config(), seed=0)
    for cell in simulation.world.cells.values():
        cell.food.stock = 19.75
        cell.food.regeneration_rate = 10.0
    agent = next(iter(simulation.world.agents.values()))
    simulation.step({agent.id: Action.wait()})
    simulation.verify_invariants()
    assert all(cell.food.stock == 20.0 for cell in simulation.world.cells.values())


@pytest.mark.parametrize("invalid_stock", [-0.01, 20.01])
def test_invariant_verification_rejects_resource_stock_outside_bounds(
    invalid_stock: float,
) -> None:
    simulation = Simulation(zero_metabolism_config(), seed=0)
    next(iter(simulation.world.cells.values())).food.stock = invalid_stock
    with pytest.raises(AssertionError, match="within capacity"):
        simulation.verify_invariants()


def test_invariant_verification_rejects_negative_inventory() -> None:
    simulation = Simulation(zero_metabolism_config(), seed=0)
    next(iter(simulation.world.agents.values())).food_inventory = -0.01
    with pytest.raises(AssertionError, match="Inventories|inventories"):
        simulation.verify_invariants()


@pytest.mark.parametrize(
    ("position", "direction"),
    [
        ((0, 0), Direction.NORTH),
        ((0, 0), Direction.WEST),
        ((2, 2), Direction.SOUTH),
        ((2, 2), Direction.EAST),
    ],
)
def test_out_of_bounds_movement_becomes_wait_and_logs_event(
    position: tuple[int, int], direction: Direction
) -> None:
    simulation = Simulation(zero_metabolism_config(), seed=0)
    agent = next(iter(simulation.world.agents.values()))
    agent.position = position

    simulation.step({agent.id: Action.move(direction)})

    assert agent.position == position
    assert isinstance(simulation.log.events[-1], InvalidActionEvent)


def test_movement_allows_shared_destination() -> None:
    config = zero_metabolism_config(initial_population=2)
    simulation = Simulation(config, seed=0, agent_ids=("a", "b"))
    simulation.world.agents["a"].position = (0, 1)
    simulation.world.agents["b"].position = (2, 1)
    simulation.step(
        {"a": Action.move(Direction.EAST), "b": Action.move(Direction.WEST)}
    )
    assert len(simulation.world.agents_at((1, 1))) == 2


def test_contested_harvest_is_independent_of_input_order() -> None:
    config = zero_metabolism_config(
        width=1,
        height=1,
        initial_population=2,
        food_initial_stock=1.0,
        food_capacity=1.0,
        food_regeneration_rate=0.0,
    )
    winners: Counter[str] = Counter()
    for seed in range(80):
        simulation = Simulation(config, seed, agent_ids=("later", "earlier"))
        simulation.step(
            {
                "later": Action.harvest(Resource.FOOD),
                "earlier": Action.harvest(Resource.FOOD),
            }
        )
        winner = next(
            event.agent_id
            for event in simulation.log.events
            if isinstance(event, HarvestEvent) and event.amount == 1.0
        )
        winners[winner] += 1
    assert set(winners) == {"earlier", "later"}
    assert all(count >= 20 for count in winners.values())


def test_contested_resolution_reproducible_across_creation_order() -> None:
    config = zero_metabolism_config(
        width=1,
        height=1,
        initial_population=2,
        food_initial_stock=1.0,
        food_capacity=1.0,
        food_regeneration_rate=0.0,
    )
    first = Simulation(config, 17, agent_ids=("a", "b"))
    second = Simulation(config, 17, agent_ids=("b", "a"))
    actions = {agent_id: Action.harvest(Resource.FOOD) for agent_id in ("a", "b")}
    first.step(actions)
    second.step(dict(reversed(tuple(actions.items()))))
    assert first.world_state_hash() == second.world_state_hash()


def test_external_action_map_requires_every_living_agent() -> None:
    simulation = Simulation(
        zero_metabolism_config(initial_population=2),
        seed=0,
        agent_ids=("a", "b"),
    )
    with pytest.raises(ValueError, match="missing living agents: b"):
        simulation.step({"a": Action.wait()})
    assert simulation.world.tick == 0


def test_external_action_map_rejects_non_action_values() -> None:
    simulation = Simulation(zero_metabolism_config(), seed=0)
    agent = next(iter(simulation.world.agents.values()))
    with pytest.raises(TypeError, match="must supply Action objects"):
        simulation.step({agent.id: "wait"})  # type: ignore[dict-item]
    assert simulation.world.tick == 0


def test_uncontested_harvest_does_not_consume_resolution_rng() -> None:
    simulation = Simulation(zero_metabolism_config(), seed=0)
    agent = next(iter(simulation.world.agents.values()))
    before = simulation._resolution_rng.state()
    simulation.step({agent.id: Action.harvest(Resource.FOOD)})
    assert simulation._resolution_rng.state() == before


def test_fully_satisfiable_harvest_group_does_not_consume_resolution_rng() -> None:
    simulation = Simulation(
        zero_metabolism_config(width=1, height=1, initial_population=2),
        seed=0,
        agent_ids=("a", "b"),
    )
    before = simulation._resolution_rng.state()
    simulation.step(
        {
            "a": Action.harvest(Resource.FOOD),
            "b": Action.harvest(Resource.FOOD),
        }
    )
    assert simulation._resolution_rng.state() == before


def test_limited_contested_harvest_consumes_resolution_rng() -> None:
    simulation = Simulation(
        zero_metabolism_config(
            width=1,
            height=1,
            initial_population=2,
            food_initial_stock=1.0,
            food_capacity=1.0,
            food_regeneration_rate=0.0,
        ),
        seed=0,
        agent_ids=("a", "b"),
    )
    before = simulation._resolution_rng.state()
    simulation.step(
        {
            "a": Action.harvest(Resource.FOOD),
            "b": Action.harvest(Resource.FOOD),
        }
    )
    assert simulation._resolution_rng.state() != before


def test_extreme_finite_harvest_fails_without_mutating_world() -> None:
    largest = sys.float_info.max
    simulation = Simulation(
        SimulationConfig(
            width=1,
            height=1,
            initial_population=1,
            food_capacity=largest,
            food_initial_stock=largest,
            food_regeneration_rate=0.0,
            initial_food_inventory=largest,
            food_productivity=largest,
            base_harvest_amount=1.0,
            food_need=0.0,
            water_need=0.0,
        ),
        seed=0,
    )
    agent = next(iter(simulation.world.agents.values()))
    before_hash = simulation.world_state_hash()
    before_rng = simulation._resolution_rng.state()
    with pytest.raises(SimulationNumericalError, match="non-finite"):
        simulation.step({agent.id: Action.harvest(Resource.FOOD)})
    assert simulation.world_state_hash() == before_hash
    assert simulation._resolution_rng.state() == before_rng
    assert simulation.log.actions == []
    assert simulation.log.events == []


def test_extreme_finite_regeneration_fails_without_mutating_world() -> None:
    largest = sys.float_info.max
    simulation = Simulation(
        SimulationConfig(
            width=1,
            height=1,
            initial_population=1,
            food_capacity=largest,
            food_initial_stock=largest,
            food_regeneration_rate=largest,
            food_need=0.0,
            water_need=0.0,
        ),
        seed=0,
    )
    agent = next(iter(simulation.world.agents.values()))
    before_hash = simulation.world_state_hash()
    with pytest.raises(SimulationNumericalError, match="non-finite"):
        simulation.step({agent.id: Action.wait()})
    assert simulation.world_state_hash() == before_hash
