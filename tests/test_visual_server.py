from __future__ import annotations

from copy import deepcopy
from threading import Event

from fastapi.testclient import TestClient

from ecb import RandomPolicy, Simulation, SimulationConfig
from ecb.visual import VisualController, VisualRuntime, VisualSubscription
from ecb.visual.server import DEFAULT_HOST, create_app


def make_session(*, seed: int = 83) -> tuple[Simulation, VisualRuntime]:
    config = SimulationConfig(width=4, height=3, initial_population=6)
    simulation = Simulation(config, seed, policy_factory=lambda _id: RandomPolicy())
    return simulation, VisualRuntime(VisualController(simulation))


def receive_initial_state(websocket) -> tuple[dict, dict]:  # type: ignore[no-untyped-def]
    snapshot = websocket.receive_json()
    status = websocket.receive_json()
    assert snapshot["type"] == "snapshot"
    assert status["type"] == "status"
    return snapshot, status


def test_server_defaults_to_loopback() -> None:
    assert DEFAULT_HOST == "127.0.0.1"


def test_health_connect_and_disconnect_are_scientifically_inert() -> None:
    class DisconnectTrackingRuntime(VisualRuntime):
        def __init__(self, controller: VisualController) -> None:
            super().__init__(controller)
            self.disconnected = Event()

        async def unregister(self, subscription: VisualSubscription) -> None:
            await super().unregister(subscription)
            self.disconnected.set()

    config = SimulationConfig(width=4, height=3, initial_population=6)
    simulation = Simulation(config, 83, policy_factory=lambda _id: RandomPolicy())
    runtime = DisconnectTrackingRuntime(VisualController(simulation))
    initial_world_hash = simulation.world_state_hash()
    initial_execution_hash = simulation.execution_state_hash()
    initial_log = deepcopy(simulation.log)

    with TestClient(create_app(runtime, start_scheduler=False)) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "ok": True,
            "playing": False,
            "speed": "1x",
            "extinct": False,
            "tick": 0,
            "scheduler_error": None,
        }

        with client.websocket_connect("/ws") as websocket:
            snapshot, status = receive_initial_state(websocket)
            assert snapshot["snapshot"]["tick"] == 0
            assert status["tick"] == 0
            assert runtime.connection_count == 1

        assert runtime.disconnected.wait(timeout=1)
        assert runtime.connection_count == 0
        assert simulation.world_state_hash() == initial_world_hash
        assert simulation.execution_state_hash() == initial_execution_hash
        assert simulation.log == initial_log


def test_websocket_controls_delegate_to_the_shared_runtime() -> None:
    simulation, runtime = make_session()

    with TestClient(create_app(runtime, start_scheduler=False)) as client:
        with client.websocket_connect("/ws") as websocket:
            receive_initial_state(websocket)

            websocket.send_json({"version": 2, "type": "play"})
            status = websocket.receive_json()
            assert status["type"] == "status"
            assert status["playing"] is True
            assert simulation.world.tick == 0

            websocket.send_json({"version": 2, "type": "set_speed", "speed": "20x"})
            status = websocket.receive_json()
            assert status["type"] == "status"
            assert status["speed"] == "20x"
            assert simulation.world.tick == 0

            websocket.send_json({"version": 2, "type": "pause"})
            status = websocket.receive_json()
            assert status["type"] == "status"
            assert status["playing"] is False
            assert simulation.world.tick == 0

            websocket.send_json({"version": 2, "type": "step"})
            snapshot = websocket.receive_json()
            assert snapshot["type"] == "snapshot"
            assert snapshot["snapshot"]["tick"] == 1
            assert simulation.world.tick == 1
            step_status = websocket.receive_json()
            assert step_status["type"] == "status"
            assert step_status["tick"] == 1


def test_protocol_errors_do_not_mutate_scientific_state() -> None:
    simulation, runtime = make_session()
    initial_world_hash = simulation.world_state_hash()
    initial_execution_hash = simulation.execution_state_hash()
    initial_log = deepcopy(simulation.log)

    malformed_messages = [
        "not-json",
        "[]",
        '{"version": 1, "type": "play"}',
        '{"version": 2, "type": "unknown"}',
        '{"version": 2, "type": "set_speed", "speed": "fast"}',
        '{"version": 2, "type": "step", "extra": true}',
    ]

    with TestClient(create_app(runtime, start_scheduler=False)) as client:
        with client.websocket_connect("/ws") as websocket:
            receive_initial_state(websocket)
            for message in malformed_messages:
                websocket.send_text(message)
                error = websocket.receive_json()
                assert error["type"] == "error"
                assert error["version"] == 2
                assert simulation.world_state_hash() == initial_world_hash
                assert simulation.execution_state_hash() == initial_execution_hash
                assert simulation.log == initial_log

            status = client.get("/health").json()
            assert status["playing"] is False
            assert status["speed"] == "1x"
            assert status["tick"] == 0


def test_two_clients_observe_one_authoritative_simulation() -> None:
    simulation, runtime = make_session()

    with TestClient(create_app(runtime, start_scheduler=False)) as client:
        with client.websocket_connect("/ws") as first:
            first_initial, _ = receive_initial_state(first)
            assert first_initial["snapshot"]["tick"] == 0

            first.send_json({"version": 2, "type": "step"})
            tick_one = first.receive_json()
            assert tick_one["snapshot"]["tick"] == 1
            first_tick_one_status = first.receive_json()
            assert first_tick_one_status["tick"] == 1

            with client.websocket_connect("/ws") as second:
                second_initial, second_status = receive_initial_state(second)
                assert second_initial["snapshot"] == tick_one["snapshot"]
                assert second_status["tick"] == 1
                assert runtime.connection_count == 2

                first.send_json({"version": 2, "type": "step"})
                first_snapshot = first.receive_json()
                second_snapshot = second.receive_json()
                assert first_snapshot["type"] == second_snapshot["type"] == "snapshot"
                assert first_snapshot["snapshot"] == second_snapshot["snapshot"]
                assert first_snapshot["snapshot"]["tick"] == 2
                assert simulation.world.tick == 2
                assert first.receive_json()["tick"] == 2
                assert second.receive_json()["tick"] == 2

    assert runtime.connection_count == 0


def test_binary_message_returns_protocol_error_and_connection_remains_usable() -> None:
    simulation, runtime = make_session()
    initial_world_hash = simulation.world_state_hash()
    initial_execution_hash = simulation.execution_state_hash()
    initial_log = deepcopy(simulation.log)

    with TestClient(create_app(runtime, start_scheduler=False)) as client:
        with client.websocket_connect("/ws") as websocket:
            receive_initial_state(websocket)
            websocket.send_bytes(b"{}")

            error = websocket.receive_json()
            assert error["type"] == "error"
            assert error["code"] == "binary_not_supported"
            assert simulation.world_state_hash() == initial_world_hash
            assert simulation.execution_state_hash() == initial_execution_hash
            assert simulation.log == initial_log

            websocket.send_json({"version": 2, "type": "step"})
            snapshot = websocket.receive_json()
            status = websocket.receive_json()
            assert snapshot["type"] == "snapshot"
            assert snapshot["snapshot"]["tick"] == 1
            assert status["type"] == "status"
            assert status["tick"] == 1


def test_sender_failure_unregisters_and_cancels_receiver(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class DisconnectTrackingRuntime(VisualRuntime):
        def __init__(self, controller: VisualController) -> None:
            super().__init__(controller)
            self.disconnected = Event()

        async def unregister(self, subscription: VisualSubscription) -> None:
            await super().unregister(subscription)
            self.disconnected.set()

    async def fail_sender(_websocket, _subscription) -> None:  # type: ignore[no-untyped-def]
        raise RuntimeError("controlled sender failure")

    config = SimulationConfig(width=4, height=3, initial_population=6)
    simulation = Simulation(config, 91, policy_factory=lambda _id: RandomPolicy())
    runtime = DisconnectTrackingRuntime(VisualController(simulation))
    monkeypatch.setattr("ecb.visual.server._send_messages", fail_sender)

    with TestClient(create_app(runtime, start_scheduler=False)) as client:
        with client.websocket_connect("/ws"):
            assert runtime.disconnected.wait(timeout=1)
        assert runtime.connection_count == 0

    assert simulation.world.tick == 0
