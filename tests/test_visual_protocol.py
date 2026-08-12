from __future__ import annotations

import pytest

from ecb import RandomPolicy, Simulation, SimulationConfig
from ecb.visual import VisualSnapshot, VisualSpeed
from ecb.visual.protocol import (
    PauseCommand,
    PlayCommand,
    ProtocolError,
    SetSpeedCommand,
    StepCommand,
    parse_client_message,
    snapshot_message,
)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ({"version": 2, "type": "play"}, PlayCommand()),
        ({"version": 2, "type": "pause"}, PauseCommand()),
        ({"version": 2, "type": "step"}, StepCommand()),
        (
            {"version": 2, "type": "set_speed", "speed": "20x"},
            SetSpeedCommand(VisualSpeed.TWENTY_X),
        ),
        (
            {"version": 2, "type": "set_speed", "speed": "max"},
            SetSpeedCommand(VisualSpeed.MAX),
        ),
    ],
)
def test_parse_supported_commands(message: object, expected: object) -> None:
    assert parse_client_message(message) == expected


@pytest.mark.parametrize(
    ("message", "code"),
    [
        ([], "invalid_message"),
        ({1: "play", "version": 2}, "invalid_message"),
        ({"version": True, "type": "play"}, "invalid_version"),
        ({"version": 1, "type": "play"}, "unsupported_version"),
        ({"version": 2}, "invalid_type"),
        ({"version": 2, "type": "unknown"}, "unknown_type"),
        ({"version": 2, "type": "play", "extra": None}, "invalid_fields"),
        ({"version": 2, "type": "set_speed"}, "invalid_fields"),
        (
            {"version": 2, "type": "set_speed", "speed": 5},
            "invalid_speed",
        ),
        (
            {"version": 2, "type": "set_speed", "speed": "fast"},
            "invalid_speed",
        ),
    ],
)
def test_parse_rejects_malformed_or_unsupported_commands(
    message: object, code: str
) -> None:
    with pytest.raises(ProtocolError) as caught:
        parse_client_message(message)

    assert caught.value.code == code


def test_snapshot_protocol_exposes_overlay_metadata_and_recent_events() -> None:
    config = SimulationConfig(width=2, height=1, initial_population=1)
    simulation = Simulation(config, 0, policy_factory=lambda _id: RandomPolicy())
    simulation.step()

    message = snapshot_message(VisualSnapshot.from_simulation(simulation))
    snapshot = message["snapshot"]

    assert isinstance(snapshot, dict)
    assert snapshot["health_reference"] == config.initial_health
    cells = snapshot["cells"]
    assert isinstance(cells, list)
    assert cells[0]["food_capacity"] == config.food_capacity  # type: ignore[index]
    assert cells[0]["water_capacity"] == config.water_capacity  # type: ignore[index]
    assert isinstance(snapshot["recent_events"], list)
