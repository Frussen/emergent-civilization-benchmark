import json
from copy import deepcopy
from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from ecb import Action, Direction, RandomPolicy, Resource, Simulation, SimulationConfig
from ecb.model import DeathEvent, HarvestEvent, InvalidActionEvent
from ecb.runner import collect_metric
from ecb.visual import (
    VisualAgent,
    VisualCell,
    VisualDeathEvent,
    VisualHarvestEvent,
    VisualInvalidActionEvent,
    VisualMetrics,
    VisualSnapshot,
    VisualWorld,
)


class NumericSubclass(float):
    pass


class VisualAgentSubclass(VisualAgent):
    pass


def visual_simulation(
    *, agent_ids: tuple[str, ...] = ("zeta", "alpha", "middle")
) -> Simulation:
    config = SimulationConfig(
        width=3,
        height=2,
        initial_population=len(agent_ids),
        observation_radius=1,
    )
    return Simulation(
        config,
        seed=17,
        policy_factory=lambda _id: RandomPolicy(),
        agent_ids=agent_ids,
    )


def scientific_rng_states(simulation: Simulation) -> tuple[object, ...]:
    return (
        simulation._initialization_rng.state(),
        simulation._resolution_rng.state(),
        tuple(
            (agent_id, rng.state())
            for agent_id, rng in sorted(simulation.policy_rngs.items())
        ),
    )


def direct_snapshot(
    *,
    agents: tuple[VisualAgent, ...] | None = None,
    cells: tuple[VisualCell, ...] | None = None,
    recent_events: tuple[
        VisualHarvestEvent | VisualDeathEvent | VisualInvalidActionEvent, ...
    ]
    | None = None,
) -> VisualSnapshot:
    return VisualSnapshot(
        tick=0,
        world_state_hash="test-hash",
        health_reference=100.0,
        world=VisualWorld(width=2, height=1),
        agents=(
            (
                VisualAgent("agent-a", 0, 0, True, 100.0, 1.0, 1.0),
                VisualAgent("agent-b", 1, 0, True, 100.0, 1.0, 1.0),
            )
            if agents is None
            else agents
        ),
        cells=(
            (
                VisualCell(0, 0, 1.0, 2.0, 1.0, 2.0),
                VisualCell(1, 0, 1.0, 2.0, 1.0, 2.0),
            )
            if cells is None
            else cells
        ),
        metrics=VisualMetrics(2, 100.0, 2.0, 2.0),
        recent_events=() if recent_events is None else recent_events,
    )


def test_snapshot_reflects_authoritative_state_and_is_detached() -> None:
    simulation = visual_simulation()
    agent = simulation.world.agents["alpha"]
    agent.position = (2, 1)
    agent.health = 42.5
    agent.food_inventory = 7.25
    agent.water_inventory = 8.5
    cell = simulation.world.cells[(2, 1)]
    cell.food.stock = 3.5
    cell.water.stock = 4.75

    snapshot = VisualSnapshot.from_simulation(simulation)
    visual_agent = snapshot.agents[0]
    visual_cell = snapshot.cells[-1]

    assert snapshot.tick == simulation.world.tick
    assert snapshot.world_state_hash == simulation.world_state_hash()
    assert (snapshot.world.width, snapshot.world.height) == (3, 2)
    assert (
        visual_agent.id,
        visual_agent.x,
        visual_agent.y,
        visual_agent.alive,
        visual_agent.health,
        visual_agent.food_inventory,
        visual_agent.water_inventory,
    ) == ("alpha", 2, 1, True, 42.5, 7.25, 8.5)
    assert (visual_cell.x, visual_cell.y) == (2, 1)
    assert (
        visual_cell.food_stock,
        visual_cell.food_capacity,
        visual_cell.water_stock,
        visual_cell.water_capacity,
    ) == (3.5, 20.0, 4.75, 20.0)
    assert snapshot.health_reference == simulation.config.initial_health

    agent.health = 1.0
    cell.food.stock = 1.0
    assert visual_agent.health == 42.5
    assert visual_cell.food_stock == 3.5
    with pytest.raises(FrozenInstanceError):
        visual_agent.health = 10.0  # type: ignore[misc]


def test_snapshot_ordering_is_explicit_and_canonical() -> None:
    simulation = visual_simulation()
    simulation.world.agents = dict(reversed(simulation.world.agents.items()))
    simulation.world.cells = dict(reversed(simulation.world.cells.items()))

    snapshot = VisualSnapshot.from_simulation(simulation)

    assert [agent.id for agent in snapshot.agents] == [
        "alpha",
        "middle",
        "zeta",
    ]
    assert [(cell.x, cell.y) for cell in snapshot.cells] == [
        (0, 0),
        (0, 1),
        (1, 0),
        (1, 1),
        (2, 0),
        (2, 1),
    ]


def test_snapshot_serialization_is_explicit_deterministic_and_detached() -> None:
    simulation = visual_simulation()
    first = VisualSnapshot.from_simulation(simulation)
    second = VisualSnapshot.from_simulation(simulation)

    first_data = first.to_json_data()
    second_data = second.to_json_data()
    first_json = json.dumps(
        first_data, allow_nan=False, sort_keys=True, separators=(",", ":")
    )
    second_json = json.dumps(
        second_data, allow_nan=False, sort_keys=True, separators=(",", ":")
    )

    assert first == second
    assert first_json == second_json
    assert first_data == second_data
    first_data["tick"] = 999
    assert first.tick == 0
    assert first.to_json_data()["tick"] == 0


def test_valid_direct_snapshot_serializes_with_standard_json_encoder() -> None:
    snapshot = direct_snapshot()

    encoded = json.dumps(snapshot.to_json_data(), allow_nan=False)

    assert json.loads(encoded) == snapshot.to_json_data()


def test_snapshot_rejects_non_finite_visual_values() -> None:
    with pytest.raises(ValueError, match="cell food stock must be finite"):
        VisualCell(0, 0, float("nan"), 1.0, 1.0, 1.0)


def test_snapshot_rejects_non_json_numeric_types() -> None:
    with pytest.raises(TypeError, match="built-in int or float"):
        VisualCell(0, 0, Decimal("1.0"), 1.0, 1.0, 1.0)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="dimensions must be integers"):
        VisualWorld(width=True, height=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="built-in int or float"):
        VisualCell(0, 0, NumericSubclass(1.0), 1.0, 1.0, 1.0)


def test_snapshot_rejects_snapshot_element_subclasses() -> None:
    subclassed_agent = VisualAgentSubclass("agent-a", 0, 0, True, 100.0, 1.0, 1.0)

    with pytest.raises(TypeError, match="tuple of VisualAgent"):
        direct_snapshot(agents=(subclassed_agent,))  # type: ignore[arg-type]


def test_snapshot_rejects_noncanonical_agent_ordering_and_duplicate_ids() -> None:
    agent_a = VisualAgent("agent-a", 0, 0, True, 100.0, 1.0, 1.0)
    agent_b = VisualAgent("agent-b", 1, 0, True, 100.0, 1.0, 1.0)

    with pytest.raises(ValueError, match="ordered canonically by ID"):
        direct_snapshot(agents=(agent_b, agent_a))
    with pytest.raises(ValueError, match="IDs must be unique"):
        direct_snapshot(agents=(agent_a, agent_a))


def test_snapshot_rejects_noncanonical_and_duplicate_cell_coordinates() -> None:
    cell_zero = VisualCell(0, 0, 1.0, 2.0, 1.0, 2.0)
    cell_one = VisualCell(1, 0, 1.0, 2.0, 1.0, 2.0)

    with pytest.raises(ValueError, match=r"ordered canonically by \(x, y\)"):
        direct_snapshot(cells=(cell_one, cell_zero))
    with pytest.raises(ValueError, match="coordinates must be unique"):
        direct_snapshot(cells=(cell_zero, cell_zero))


def test_snapshot_creation_does_not_change_any_simulation_state() -> None:
    simulation = visual_simulation()
    before_world_hash = simulation.world_state_hash()
    before_execution_hash = simulation.execution_state_hash()
    before_tick = simulation.world.tick
    before_rngs = scientific_rng_states(simulation)
    before_policy_state = {
        agent_id: policy.continuation_state()
        for agent_id, policy in simulation.policies.items()
    }
    before_log = deepcopy(simulation.log)

    for _ in range(1_000):
        VisualSnapshot.from_simulation(simulation)

    assert simulation.world_state_hash() == before_world_hash
    assert simulation.execution_state_hash() == before_execution_hash
    assert simulation.world.tick == before_tick
    assert scientific_rng_states(simulation) == before_rngs
    assert {
        agent_id: policy.continuation_state()
        for agent_id, policy in simulation.policies.items()
    } == before_policy_state
    assert simulation.log == before_log


def test_multi_occupancy_and_dead_agents_remain_distinct() -> None:
    simulation = visual_simulation(agent_ids=("alive-b", "dead", "alive-a"))
    for agent in simulation.world.agents.values():
        agent.position = (1, 1)
    simulation.world.agents["dead"].health = 0.0

    snapshot = VisualSnapshot.from_simulation(simulation)

    assert [(agent.id, agent.x, agent.y) for agent in snapshot.agents] == [
        ("alive-a", 1, 1),
        ("alive-b", 1, 1),
        ("dead", 1, 1),
    ]
    assert [agent.alive for agent in snapshot.agents] == [True, True, False]
    assert snapshot.metrics.alive_agents == 2


def test_visual_metrics_match_headless_runner_semantics() -> None:
    simulation = visual_simulation(agent_ids=("alive-a", "alive-b", "dead"))
    simulation.world.agents["alive-a"].health = 30.0
    simulation.world.agents["alive-b"].health = 60.0
    simulation.world.agents["dead"].health = 0.0
    for index, cell in enumerate(simulation.world.cells.values(), start=1):
        cell.food.stock = float(index)
        cell.water.stock = float(index + 1)

    visual = VisualSnapshot.from_simulation(simulation).metrics
    headless = collect_metric(simulation)

    assert visual.alive_agents == headless.alive_agents == 2
    assert visual.mean_health_alive == headless.mean_health_alive == 45.0
    assert visual.total_world_food == headless.total_world_food
    assert visual.total_world_water == headless.total_world_water


def test_mean_health_is_none_when_population_is_extinct() -> None:
    simulation = visual_simulation(agent_ids=("dead",))
    simulation.world.agents["dead"].health = 0.0

    snapshot = VisualSnapshot.from_simulation(simulation)

    assert snapshot.metrics.alive_agents == 0
    assert snapshot.metrics.mean_health_alive is None


def test_capacities_and_health_reference_are_authoritative_and_detached() -> None:
    simulation = visual_simulation()
    cell = simulation.world.cells[(0, 0)]
    cell.food.capacity = 31.5
    cell.water.capacity = 47.25
    snapshot = VisualSnapshot.from_simulation(simulation)
    visual_cell = snapshot.cells[0]

    assert visual_cell.food_capacity == 31.5
    assert visual_cell.water_capacity == 47.25
    assert snapshot.health_reference == simulation.config.initial_health

    cell.food.capacity = 99.0
    cell.water.capacity = 98.0
    assert visual_cell.food_capacity == 31.5
    assert visual_cell.water_capacity == 47.25


def test_recent_events_preserve_canonical_order_and_serialize_explicitly() -> None:
    simulation = visual_simulation()
    simulation.log.events.extend(
        [
            HarvestEvent(2, "alpha", Resource.FOOD, 1.5, (1, 0)),
            InvalidActionEvent(
                2,
                "middle",
                Action.move(Direction.NORTH),
                "movement outside world boundary",
            ),
            DeathEvent(3, "zeta"),
        ]
    )

    snapshot = VisualSnapshot.from_simulation(simulation)

    assert snapshot.recent_events == (
        VisualHarvestEvent(2, "alpha", "food", 1.5, 1, 0),
        VisualInvalidActionEvent(
            2,
            "middle",
            "move",
            "north",
            None,
            "movement outside world boundary",
        ),
        VisualDeathEvent(3, "zeta"),
    )
    assert snapshot.to_json_data()["recent_events"] == [
        {
            "event_type": "harvest",
            "tick": 2,
            "agent_id": "alpha",
            "resource": "food",
            "amount": 1.5,
            "x": 1,
            "y": 0,
        },
        {
            "event_type": "invalid_action",
            "tick": 2,
            "agent_id": "middle",
            "action_kind": "move",
            "direction": "north",
            "resource": None,
            "reason": "movement outside world boundary",
        },
        {"event_type": "death", "tick": 3, "agent_id": "zeta"},
    ]


@pytest.mark.parametrize(
    ("action_kind", "direction", "resource"),
    [
        ("wait", None, None),
        *(("move", direction.value, None) for direction in Direction),
        *(("harvest", None, resource.value) for resource in Resource),
    ],
)
def test_visual_invalid_action_accepts_and_serializes_every_canonical_shape(
    action_kind: str,
    direction: str | None,
    resource: str | None,
) -> None:
    event = VisualInvalidActionEvent(
        0,
        "agent-a",
        action_kind,
        direction,
        resource,
        "canonical action was invalid in context",
    )

    payload = direct_snapshot(recent_events=(event,)).to_json_data()["recent_events"][0]

    assert isinstance(payload, dict)
    assert payload["action_kind"] == action_kind
    assert payload["direction"] == direction
    assert payload["resource"] == resource


@pytest.mark.parametrize(
    ("action_kind", "direction", "resource", "message"),
    [
        ("wait", "north", None, "only visual MOVE accepts a direction"),
        ("wait", None, "food", "only visual HARVEST accepts a resource"),
        ("move", None, None, "visual MOVE requires a direction"),
        ("move", "north", "food", "only visual HARVEST accepts a resource"),
        ("harvest", "north", "food", "only visual MOVE accepts a direction"),
        ("harvest", None, None, "visual HARVEST requires a resource"),
    ],
)
def test_visual_invalid_action_rejects_noncanonical_shape_before_serialization(
    action_kind: str,
    direction: str | None,
    resource: str | None,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        VisualInvalidActionEvent(
            0,
            "agent-a",
            action_kind,
            direction,
            resource,
            "invalid shape",
        )


@pytest.mark.parametrize("amount", [0, 2, 1.5])
def test_visual_harvest_accepts_and_serializes_nonnegative_amount(
    amount: int | float,
) -> None:
    event = VisualHarvestEvent(0, "agent-a", "food", amount, 0, 0)

    payload = direct_snapshot(recent_events=(event,)).to_json_data()["recent_events"][0]

    assert isinstance(payload, dict)
    assert payload["amount"] == amount


@pytest.mark.parametrize("amount", [-1, -0.25])
def test_visual_harvest_rejects_negative_amount(amount: int | float) -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        VisualHarvestEvent(0, "agent-a", "food", amount, 0, 0)


@pytest.mark.parametrize("amount", [float("nan"), float("inf"), float("-inf")])
def test_visual_harvest_rejects_nonfinite_amount(amount: float) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        VisualHarvestEvent(0, "agent-a", "food", amount, 0, 0)


@pytest.mark.parametrize("amount", [True, Decimal("1.0"), NumericSubclass(1.0)])
def test_visual_harvest_rejects_non_builtin_numeric_type(amount: object) -> None:
    with pytest.raises(TypeError, match="built-in int or float"):
        VisualHarvestEvent(0, "agent-a", "food", amount, 0, 0)


def test_recent_events_are_a_bounded_detached_tail() -> None:
    simulation = visual_simulation()
    simulation.log.events.extend(
        HarvestEvent(tick, "alpha", Resource.WATER, 1.0, (0, 0)) for tick in range(100)
    )

    snapshot = VisualSnapshot.from_simulation(simulation)

    assert len(snapshot.recent_events) == 75
    assert snapshot.recent_events[0].tick == 25
    assert snapshot.recent_events[-1].tick == 99
    simulation.log.events.clear()
    assert len(snapshot.recent_events) == 75
