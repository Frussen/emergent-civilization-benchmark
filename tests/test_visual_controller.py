import pytest

from ecb import (
    OracleSurvivalPolicy,
    RandomPolicy,
    Simulation,
    SimulationConfig,
)
from ecb.visual import VisualController, VisualSpeed


def simulation_for_policy(policy_name: str, *, seed: int = 23) -> Simulation:
    config = SimulationConfig(
        width=5,
        height=4,
        initial_population=10,
        observation_radius=2,
    )
    if policy_name == "random":
        return Simulation(config, seed, policy_factory=lambda _id: RandomPolicy())
    if policy_name == "oracle":
        return Simulation(
            config,
            seed,
            policy_factory=lambda _id: OracleSurvivalPolicy(
                food_need=config.food_need,
                water_need=config.water_need,
                base_harvest_amount=config.base_harvest_amount,
            ),
        )
    raise AssertionError(f"unsupported test policy: {policy_name}")


def test_controller_starts_paused_at_one_x() -> None:
    controller = VisualController(simulation_for_policy("random"))

    assert controller.is_playing is False
    assert controller.speed is VisualSpeed.ONE_X


def test_non_step_operations_change_only_controller_state() -> None:
    simulation = simulation_for_policy("random")
    controller = VisualController(simulation)
    initial_hash = simulation.execution_state_hash()
    initial_tick = simulation.world.tick

    controller.current_snapshot()
    assert simulation.execution_state_hash() == initial_hash
    controller.play()
    assert controller.is_playing is True
    assert simulation.execution_state_hash() == initial_hash
    controller.set_speed(VisualSpeed.TWENTY_X)
    assert controller.speed is VisualSpeed.TWENTY_X
    assert simulation.execution_state_hash() == initial_hash
    controller.pause()
    assert controller.is_playing is False
    assert simulation.execution_state_hash() == initial_hash
    assert simulation.world.tick == initial_tick


def test_invalid_speed_is_rejected_without_changing_state() -> None:
    simulation = simulation_for_policy("random")
    controller = VisualController(simulation)
    initial_hash = simulation.execution_state_hash()

    with pytest.raises(TypeError, match="speed must be a VisualSpeed"):
        controller.set_speed("5x")  # type: ignore[arg-type]

    assert controller.speed is VisualSpeed.ONE_X
    assert simulation.execution_state_hash() == initial_hash


def test_step_advances_exactly_one_canonical_tick() -> None:
    simulation = simulation_for_policy("random")
    controller = VisualController(simulation)

    snapshot = controller.step()

    assert simulation.world.tick == 1
    assert snapshot.tick == 1
    assert snapshot.world_state_hash == simulation.world_state_hash()
    assert len(simulation.log.metrics) == 1


def test_advance_executes_one_tick_without_snapshot_capture(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    simulation = simulation_for_policy("random")
    controller = VisualController(simulation)

    def fail_snapshot_capture(_simulation):  # type: ignore[no-untyped-def]
        raise AssertionError("advance must not capture a snapshot")

    monkeypatch.setattr(
        "ecb.visual.controller.VisualSnapshot.from_simulation", fail_snapshot_capture
    )

    controller.advance()

    assert simulation.world.tick == 1
    assert len(simulation.log.metrics) == 1


@pytest.mark.parametrize("policy_name", ["random", "oracle"])
def test_visual_and_headless_hash_trajectories_match(policy_name: str) -> None:
    direct = simulation_for_policy(policy_name)
    visual_simulation = simulation_for_policy(policy_name)
    controller = VisualController(visual_simulation)

    assert controller.current_snapshot().world_state_hash == direct.world_state_hash()
    for tick in range(1, 31):
        direct.step()
        controller.current_snapshot()
        controller.play()
        controller.set_speed(VisualSpeed.MAX if tick % 2 else VisualSpeed.FIVE_X)
        controller.pause()
        snapshot = controller.step()
        controller.current_snapshot()

        assert snapshot.tick == tick
        assert snapshot.world_state_hash == direct.world_state_hash()
        assert visual_simulation.execution_state_hash() == direct.execution_state_hash()

    assert visual_simulation.log.actions == direct.log.actions
    assert visual_simulation.log.events == direct.log.events
    assert visual_simulation.log.metrics == direct.log.metrics
    assert visual_simulation.log.tick == direct.log.tick


@pytest.mark.parametrize("policy_name", ["random", "oracle"])
def test_step_while_playing_matches_headless_trajectory(policy_name: str) -> None:
    direct = simulation_for_policy(policy_name, seed=41)
    visual_simulation = simulation_for_policy(policy_name, seed=41)
    controller = VisualController(visual_simulation)
    controller.play()

    for tick in range(1, 21):
        direct.step()
        snapshot = controller.step()

        assert controller.is_playing is True
        assert snapshot.tick == tick
        assert snapshot.world_state_hash == direct.world_state_hash()

    assert visual_simulation.log.actions == direct.log.actions
    assert visual_simulation.log.events == direct.log.events
    assert visual_simulation.log.metrics == direct.log.metrics
    assert visual_simulation.log.tick == direct.log.tick


def test_one_or_one_thousand_snapshots_have_the_same_later_trajectory() -> None:
    once = simulation_for_policy("random", seed=31)
    many = simulation_for_policy("random", seed=31)
    once_controller = VisualController(once)
    many_controller = VisualController(many)

    once_controller.current_snapshot()
    for _ in range(1_000):
        many_controller.current_snapshot()

    for _ in range(20):
        assert (
            once_controller.step().world_state_hash
            == many_controller.step().world_state_hash
        )


def test_step_after_extinction_delegates_to_canonical_simulation() -> None:
    config = SimulationConfig(
        width=2,
        height=2,
        initial_population=1,
        initial_health=1.0,
        initial_food_inventory=0.0,
        initial_water_inventory=0.0,
        food_initial_stock=0.0,
        water_initial_stock=0.0,
        food_regeneration_rate=0.0,
        water_regeneration_rate=0.0,
    )
    direct = Simulation(config, 7, policy_factory=lambda _id: RandomPolicy())
    visual_simulation = Simulation(config, 7, policy_factory=lambda _id: RandomPolicy())
    controller = VisualController(visual_simulation)

    direct.step()
    extinct_snapshot = controller.step()
    assert extinct_snapshot.metrics.alive_agents == 0
    assert extinct_snapshot.tick == 1

    direct.step()
    post_extinction_snapshot = controller.step()
    assert post_extinction_snapshot.tick == 2
    assert post_extinction_snapshot.metrics.alive_agents == 0
    assert post_extinction_snapshot.world_state_hash == direct.world_state_hash()
