from __future__ import annotations

import asyncio
import json
from copy import deepcopy

import pytest

from ecb import OracleSurvivalPolicy, RandomPolicy, Simulation, SimulationConfig
from ecb.visual import VisualController, VisualRuntime, VisualSnapshot, VisualSpeed
from ecb.visual.protocol import ProtocolError
from ecb.visual.runtime import TICKS_PER_SECOND, next_pacing_deadline


async def receive_message(subscription) -> dict:  # type: ignore[no-untyped-def]
    return json.loads(await subscription.receive_text())


def simulation_for_policy(policy_name: str, *, seed: int = 59) -> Simulation:
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


def assert_simulations_equivalent(actual: Simulation, expected: Simulation) -> None:
    assert actual.world.tick == expected.world.tick
    assert actual.world_state_hash() == expected.world_state_hash()
    assert actual.execution_state_hash() == expected.execution_state_hash()
    assert actual.log.tick == expected.log.tick
    assert actual.log.actions == expected.log.actions
    assert actual.log.events == expected.log.events
    assert actual.log.metrics == expected.log.metrics


def test_finite_speed_pacing_contract() -> None:
    assert TICKS_PER_SECOND == {
        VisualSpeed.ONE_X: 1,
        VisualSpeed.FIVE_X: 5,
        VisualSpeed.TWENTY_X: 20,
    }
    assert VisualSpeed.MAX not in TICKS_PER_SECOND


def test_pacing_deadlines_do_not_add_processing_time_or_catch_up_debt() -> None:
    assert next_pacing_deadline(10.0, 10.02, 0.05) == 10.05
    assert next_pacing_deadline(10.0, 10.20, 0.05) == 10.20


def test_observation_and_presentation_operations_do_not_change_science() -> None:
    async def scenario() -> None:
        simulation = simulation_for_policy("random")
        runtime = VisualRuntime(VisualController(simulation))
        initial_world_hash = simulation.world_state_hash()
        initial_execution_hash = simulation.execution_state_hash()
        initial_log = deepcopy(simulation.log)

        subscription = await runtime.register()
        await receive_message(subscription)
        await receive_message(subscription)
        await runtime.current_snapshot()
        await runtime.status()
        await runtime.play()
        await receive_message(subscription)
        await runtime.pause()
        await receive_message(subscription)
        await runtime.set_speed(VisualSpeed.TWENTY_X)
        await receive_message(subscription)
        await runtime.unregister(subscription)

        assert runtime.connection_count == 0
        assert simulation.world_state_hash() == initial_world_hash
        assert simulation.execution_state_hash() == initial_execution_hash
        assert simulation.log == initial_log
        await runtime.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("policy_name", ["random", "oracle"])
@pytest.mark.parametrize(
    "speed",
    [
        VisualSpeed.ONE_X,
        VisualSpeed.FIVE_X,
        VisualSpeed.TWENTY_X,
        VisualSpeed.MAX,
    ],
)
def test_fixed_scheduled_ticks_match_headless_at_every_speed(
    policy_name: str, speed: VisualSpeed
) -> None:
    async def scenario() -> None:
        direct = simulation_for_policy(policy_name)
        scheduled = simulation_for_policy(policy_name)
        runtime = VisualRuntime(VisualController(scheduled))
        await runtime.set_speed(speed)
        await runtime.play()

        for tick in range(1, 21):
            direct.step()
            snapshot = await runtime.advance_scheduled_once()

            assert snapshot is not None
            assert snapshot.tick == tick
            assert snapshot.world_state_hash == direct.world_state_hash()
            assert_simulations_equivalent(scheduled, direct)
        await runtime.close()

    asyncio.run(scenario())


def test_scheduler_pauses_at_extinction_but_manual_step_remains_legal() -> None:
    async def scenario() -> None:
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
        simulation = Simulation(config, 7, policy_factory=lambda _id: RandomPolicy())
        runtime = VisualRuntime(VisualController(simulation))
        await runtime.play()

        final_snapshot = await runtime.advance_scheduled_once()
        assert final_snapshot is not None
        assert final_snapshot.tick == 1
        assert final_snapshot.metrics.alive_agents == 0
        assert (await runtime.status()).playing is False
        assert (await runtime.status()).extinct is True

        assert await runtime.advance_scheduled_once() is None
        assert simulation.world.tick == 1

        manual_snapshot = await runtime.step()
        assert manual_snapshot.tick == 2
        assert manual_snapshot.metrics.alive_agents == 0
        await runtime.close()

    asyncio.run(scenario())


def test_snapshot_capture_cannot_interleave_with_a_step() -> None:
    async def scenario() -> None:
        simulation = simulation_for_policy("random")
        runtime = VisualRuntime(VisualController(simulation))

        await runtime._access_lock.acquire()
        step_task = asyncio.create_task(runtime.step())
        await asyncio.sleep(0)
        snapshot_task = asyncio.create_task(runtime.current_snapshot())
        await asyncio.sleep(0)
        assert step_task.done() is False
        assert snapshot_task.done() is False

        runtime._access_lock.release()
        stepped, observed = await asyncio.gather(step_task, snapshot_task)
        assert stepped.tick == observed.tick == 1
        assert stepped.world_state_hash == observed.world_state_hash
        assert observed.world_state_hash == simulation.world_state_hash()
        await runtime.close()

    asyncio.run(scenario())


def test_slow_subscriber_keeps_only_newest_snapshot_without_losing_ticks() -> None:
    async def scenario() -> None:
        direct = simulation_for_policy("random", seed=73)
        scheduled = simulation_for_policy("random", seed=73)
        runtime = VisualRuntime(VisualController(scheduled))
        subscription = await runtime.register()
        await receive_message(subscription)
        await receive_message(subscription)
        await runtime.play()
        await receive_message(subscription)

        for _ in range(40):
            direct.step()
            await runtime.advance_scheduled_once()

        await runtime.pause()
        assert subscription.pending_snapshot_count == 1
        assert subscription.pending_reliable_count == 1
        newest = await receive_message(subscription)
        assert newest["type"] == "snapshot"
        assert newest["snapshot"]["tick"] == 40  # type: ignore[index]
        assert newest["snapshot"]["world_state_hash"] == direct.world_state_hash()  # type: ignore[index]
        reliable_status = await receive_message(subscription)
        assert reliable_status["type"] == "status"
        assert reliable_status["playing"] is False
        assert_simulations_equivalent(scheduled, direct)
        await runtime.close()

    asyncio.run(scenario())


def test_manual_step_snapshot_precedes_its_status() -> None:
    async def scenario() -> None:
        runtime = VisualRuntime(VisualController(simulation_for_policy("random")))
        subscription = await runtime.register()
        await receive_message(subscription)
        await receive_message(subscription)

        await runtime.step()

        snapshot = await receive_message(subscription)
        status = await receive_message(subscription)
        assert snapshot["type"] == "snapshot"
        assert status["type"] == "status"
        assert snapshot["snapshot"]["tick"] == status["tick"] == 1
        await runtime.close()

    asyncio.run(scenario())


def test_full_reliable_mailbox_never_blocks_step_or_healthy_client() -> None:
    async def scenario() -> None:
        simulation = simulation_for_policy("random")
        runtime = VisualRuntime(VisualController(simulation), reliable_queue_limit=2)
        slow = await runtime.register()
        healthy = await runtime.register()
        await receive_message(healthy)
        await receive_message(healthy)

        await runtime.publish_protocol_error(
            slow, ProtocolError("test_error", "fill the reliable mailbox")
        )
        assert slow.pending_reliable_count == 2

        play_task = asyncio.create_task(runtime.play())
        step_task = asyncio.create_task(runtime.step())
        play_status, snapshot = await asyncio.wait_for(
            asyncio.gather(play_task, step_task), timeout=1
        )

        assert play_status.playing is True
        assert snapshot.tick == simulation.world.tick == 1
        assert slow.is_closed is True
        assert runtime.connection_count == 1

        healthy_play = await receive_message(healthy)
        healthy_snapshot = await receive_message(healthy)
        healthy_step_status = await receive_message(healthy)
        assert healthy_play["type"] == "status"
        assert healthy_snapshot["type"] == "snapshot"
        assert healthy_snapshot["snapshot"]["tick"] == 1
        assert healthy_step_status["type"] == "status"
        assert healthy_step_status["tick"] == 1
        await runtime.close()

    asyncio.run(scenario())


def test_manual_and_scheduled_steps_are_complete_and_sequential() -> None:
    async def scenario() -> None:
        direct = simulation_for_policy("random", seed=101)
        visual = simulation_for_policy("random", seed=101)
        runtime = VisualRuntime(VisualController(visual))
        await runtime.play()

        await runtime._publication_lock.acquire()
        scheduled = asyncio.create_task(runtime.advance_scheduled_once())
        await asyncio.sleep(0)
        manual = asyncio.create_task(runtime.step())
        await asyncio.sleep(0)
        assert scheduled.done() is False
        assert manual.done() is False
        runtime._publication_lock.release()
        scheduled_snapshot, manual_snapshot = await asyncio.gather(scheduled, manual)

        direct.step()
        direct.step()
        assert scheduled_snapshot is not None
        assert scheduled_snapshot.tick == 1
        assert manual_snapshot.tick == 2
        assert_simulations_equivalent(visual, direct)
        await runtime.close()

    asyncio.run(scenario())


def test_repeated_and_concurrent_play_reuse_one_scheduler_task() -> None:
    async def scenario() -> None:
        runtime = VisualRuntime(VisualController(simulation_for_policy("random")))
        await runtime.start()
        scheduler = runtime.scheduler_task

        await runtime.play()
        await runtime.play()
        await asyncio.gather(runtime.play(), runtime.play())

        assert scheduler is not None
        assert runtime.scheduler_task is scheduler
        assert scheduler.done() is False
        await runtime.pause()
        await runtime.close()

    asyncio.run(scenario())


def test_scheduler_failure_pauses_reports_and_keeps_one_live_scheduler() -> None:
    class FailingRuntime(VisualRuntime):
        def __init__(self, controller: VisualController) -> None:
            super().__init__(controller)
            self.failure_handled = asyncio.Event()

        def _controller_advance(self) -> None:
            raise RuntimeError("controlled scheduler failure")

        async def _handle_scheduler_failure(self, error: Exception) -> None:
            await super()._handle_scheduler_failure(error)
            self.failure_handled.set()

    async def scenario() -> None:
        simulation = simulation_for_policy("random")
        runtime = FailingRuntime(VisualController(simulation))
        subscription = await runtime.register()
        await receive_message(subscription)
        await receive_message(subscription)
        await runtime.set_speed(VisualSpeed.MAX)
        await receive_message(subscription)
        await runtime.start()
        scheduler = runtime.scheduler_task
        await runtime.play()

        play_status = await receive_message(subscription)
        error = await receive_message(subscription)
        failed_status = await receive_message(subscription)
        await runtime.failure_handled.wait()
        await asyncio.sleep(0)

        assert play_status["playing"] is True
        assert error["type"] == "error"
        assert error["code"] == "scheduler_error"
        assert failed_status["playing"] is False
        assert "controlled scheduler failure" in failed_status["scheduler_error"]
        assert simulation.world.tick == 0
        assert scheduler is not None
        assert runtime.scheduler_task is scheduler
        assert scheduler.done() is False
        await runtime.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("policy_name", ["random", "oracle"])
def test_max_snapshot_throttling_changes_only_observation_frequency(
    policy_name: str, monkeypatch
) -> None:
    async def scenario() -> None:
        direct = simulation_for_policy(policy_name, seed=109)
        visual = simulation_for_policy(policy_name, seed=109)
        runtime = VisualRuntime(VisualController(visual))
        subscription = await runtime.register()
        await receive_message(subscription)
        await receive_message(subscription)
        await runtime.set_speed(VisualSpeed.MAX)
        await receive_message(subscription)
        await runtime.play()
        await receive_message(subscription)

        snapshot_captures = 0
        original_snapshot = VisualController.current_snapshot

        def counted_snapshot(controller: VisualController) -> VisualSnapshot:
            nonlocal snapshot_captures
            snapshot_captures += 1
            return original_snapshot(controller)

        monkeypatch.setattr(VisualController, "current_snapshot", counted_snapshot)

        for tick in range(1, 31):
            direct.step()
            snapshot = await runtime.advance_scheduled_once(publish_snapshot=tick == 30)
            if tick < 30:
                assert snapshot is None

        assert subscription.pending_snapshot_count == 1
        assert snapshot_captures == 1
        newest = await receive_message(subscription)
        assert newest["snapshot"]["tick"] == 30
        assert_simulations_equivalent(visual, direct)
        await runtime.close()

    asyncio.run(scenario())


def test_snapshot_is_encoded_once_and_shared_across_clients(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def scenario() -> None:
        simulation = simulation_for_policy("random")
        runtime = VisualRuntime(VisualController(simulation))
        first = await runtime.register()
        second = await runtime.register()
        await receive_message(first)
        await receive_message(first)
        await receive_message(second)
        await receive_message(second)

        calls = 0
        original = VisualSnapshot.to_json_data

        def counted(snapshot: VisualSnapshot):  # type: ignore[no-untyped-def]
            nonlocal calls
            calls += 1
            return original(snapshot)

        monkeypatch.setattr(VisualSnapshot, "to_json_data", counted)
        await runtime.step()
        first_text = await first.receive_text()
        second_text = await second.receive_text()

        assert calls == 1
        assert first_text is second_text
        assert json.loads(first_text)["snapshot"]["tick"] == 1
        await runtime.close()

    asyncio.run(scenario())


def test_close_is_terminal_and_queued_step_cannot_run_late() -> None:
    async def scenario() -> None:
        simulation = simulation_for_policy("random")
        runtime = VisualRuntime(VisualController(simulation))

        await runtime._access_lock.acquire()
        step_task = asyncio.create_task(runtime.step())
        await asyncio.sleep(0)
        close_task = asyncio.create_task(runtime.close())
        await asyncio.sleep(0)
        runtime._access_lock.release()

        with pytest.raises(RuntimeError, match="visual runtime is closed"):
            await step_task
        await close_task
        assert simulation.world.tick == 0

        operations = (
            runtime.step(),
            runtime.play(),
            runtime.pause(),
            runtime.set_speed(VisualSpeed.FIVE_X),
            runtime.status(),
            runtime.current_snapshot(),
            runtime.register(),
            runtime.start(),
        )
        for operation in operations:
            with pytest.raises(RuntimeError, match="visual runtime is closed"):
                await operation
        await runtime.close()

    asyncio.run(scenario())


def test_shutdown_during_playback_cancels_background_work() -> None:
    class SignalingRuntime(VisualRuntime):
        def __init__(self, controller: VisualController) -> None:
            super().__init__(controller)
            self.advance_entered = asyncio.Event()

        def _controller_advance(self) -> None:
            self.advance_entered.set()
            super()._controller_advance()

    async def scenario() -> None:
        simulation = simulation_for_policy("random")
        runtime = SignalingRuntime(VisualController(simulation))
        await runtime.set_speed(VisualSpeed.MAX)
        await runtime.start()
        await runtime.play()
        await runtime.advance_entered.wait()
        tick_before_close = simulation.world.tick

        await asyncio.wait_for(runtime.close(), timeout=1)

        assert runtime.scheduler_task is None
        assert tick_before_close >= 1
        assert simulation.world.tick == tick_before_close

    asyncio.run(scenario())


def test_actual_scheduler_publishes_fatal_snapshot_before_paused_status() -> None:
    async def scenario() -> None:
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
        simulation = Simulation(config, 7, policy_factory=lambda _id: RandomPolicy())
        runtime = VisualRuntime(VisualController(simulation))
        subscription = await runtime.register()
        await receive_message(subscription)
        await receive_message(subscription)
        await runtime.set_speed(VisualSpeed.MAX)
        await receive_message(subscription)
        await runtime.start()
        await runtime.play()
        await receive_message(subscription)

        fatal_snapshot = await receive_message(subscription)
        extinct_status = await receive_message(subscription)
        assert fatal_snapshot["type"] == "snapshot"
        assert fatal_snapshot["snapshot"]["tick"] == 1
        assert extinct_status["type"] == "status"
        assert extinct_status["tick"] == 1
        assert extinct_status["extinct"] is True
        assert extinct_status["playing"] is False

        await asyncio.sleep(0)
        assert simulation.world.tick == 1
        await runtime.close()

    asyncio.run(scenario())


def test_max_scheduler_runs_and_yields_to_control_operations() -> None:
    async def scenario() -> None:
        simulation = simulation_for_policy("random")
        runtime = VisualRuntime(VisualController(simulation))
        await runtime.set_speed(VisualSpeed.MAX)
        await runtime.start()
        await runtime.play()

        async with asyncio.timeout(2):
            while (await runtime.status()).tick < 3:
                await asyncio.sleep(0)
        await runtime.pause()
        paused_tick = (await runtime.status()).tick
        for _ in range(5):
            await asyncio.sleep(0)
        assert (await runtime.status()).tick == paused_tick
        await runtime.close()

    asyncio.run(scenario())
