from __future__ import annotations

import pytest

from ecb.visual import VisualSpeed
from ecb.visual.protocol import (
    PauseCommand,
    PlayCommand,
    ProtocolError,
    SetSpeedCommand,
    StepCommand,
    parse_client_message,
)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ({"version": 1, "type": "play"}, PlayCommand()),
        ({"version": 1, "type": "pause"}, PauseCommand()),
        ({"version": 1, "type": "step"}, StepCommand()),
        (
            {"version": 1, "type": "set_speed", "speed": "20x"},
            SetSpeedCommand(VisualSpeed.TWENTY_X),
        ),
        (
            {"version": 1, "type": "set_speed", "speed": "max"},
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
        ({1: "play", "version": 1}, "invalid_message"),
        ({"version": True, "type": "play"}, "invalid_version"),
        ({"version": 2, "type": "play"}, "unsupported_version"),
        ({"version": 1}, "invalid_type"),
        ({"version": 1, "type": "unknown"}, "unknown_type"),
        ({"version": 1, "type": "play", "extra": None}, "invalid_fields"),
        ({"version": 1, "type": "set_speed"}, "invalid_fields"),
        (
            {"version": 1, "type": "set_speed", "speed": 5},
            "invalid_speed",
        ),
        (
            {"version": 1, "type": "set_speed", "speed": "fast"},
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
