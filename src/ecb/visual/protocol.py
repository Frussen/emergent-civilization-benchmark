"""Explicit versioned JSON protocol for the M1 visual backend."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import cast

from ecb.visual.controller import VisualSpeed
from ecb.visual.snapshot import JsonValue, VisualSnapshot

PROTOCOL_VERSION = 2


class ProtocolError(ValueError):
    """A client message violated the visual protocol contract."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class PlayCommand:
    pass


@dataclass(frozen=True, slots=True)
class PauseCommand:
    pass


@dataclass(frozen=True, slots=True)
class StepCommand:
    pass


@dataclass(frozen=True, slots=True)
class SetSpeedCommand:
    speed: VisualSpeed


type ClientCommand = PlayCommand | PauseCommand | StepCommand | SetSpeedCommand
type ServerMessage = dict[str, JsonValue]
type EncodedServerMessage = str


def parse_client_message(value: object) -> ClientCommand:
    """Validate and parse one protocol-v2 client command."""
    if type(value) is not dict:
        raise ProtocolError("invalid_message", "message must be a JSON object")
    if any(type(key) is not str for key in value):
        raise ProtocolError("invalid_message", "message keys must be strings")
    message = cast(dict[str, object], value)

    version = message.get("version")
    if type(version) is not int:
        raise ProtocolError("invalid_version", "version must be an integer")
    if version != PROTOCOL_VERSION:
        raise ProtocolError(
            "unsupported_version",
            f"unsupported protocol version {version}; expected {PROTOCOL_VERSION}",
        )

    message_type = message.get("type")
    if type(message_type) is not str:
        raise ProtocolError("invalid_type", "type must be a string")

    if message_type == "play":
        _require_exact_fields(message, {"version", "type"})
        return PlayCommand()
    if message_type == "pause":
        _require_exact_fields(message, {"version", "type"})
        return PauseCommand()
    if message_type == "step":
        _require_exact_fields(message, {"version", "type"})
        return StepCommand()
    if message_type == "set_speed":
        _require_exact_fields(message, {"version", "type", "speed"})
        speed = message["speed"]
        if type(speed) is not str:
            raise ProtocolError("invalid_speed", "speed must be a string")
        try:
            visual_speed = VisualSpeed(speed)
        except ValueError as error:
            allowed = ", ".join(item.value for item in VisualSpeed)
            raise ProtocolError(
                "invalid_speed", f"unsupported speed {speed!r}; expected: {allowed}"
            ) from error
        return SetSpeedCommand(visual_speed)

    raise ProtocolError("unknown_type", f"unknown message type {message_type!r}")


def snapshot_message(snapshot: VisualSnapshot) -> ServerMessage:
    return {
        "version": PROTOCOL_VERSION,
        "type": "snapshot",
        "snapshot": snapshot.to_json_data(),
    }


def status_message(
    *,
    playing: bool,
    speed: VisualSpeed,
    extinct: bool,
    tick: int,
    scheduler_error: str | None = None,
) -> ServerMessage:
    return {
        "version": PROTOCOL_VERSION,
        "type": "status",
        "playing": playing,
        "speed": speed.value,
        "extinct": extinct,
        "tick": tick,
        "scheduler_error": scheduler_error,
    }


def error_message(error: ProtocolError) -> ServerMessage:
    return {
        "version": PROTOCOL_VERSION,
        "type": "error",
        "code": error.code,
        "message": error.message,
    }


def server_error_message(*, code: str, message: str) -> ServerMessage:
    return {
        "version": PROTOCOL_VERSION,
        "type": "error",
        "code": code,
        "message": message,
    }


def encode_server_message(message: ServerMessage) -> EncodedServerMessage:
    """Encode one explicit server message as compact standards-compliant JSON."""
    return json.dumps(message, allow_nan=False, separators=(",", ":"))


def _require_exact_fields(value: dict[str, object], expected: set[str]) -> None:
    actual = set(value)
    if actual == expected:
        return
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    details = []
    if missing:
        details.append("missing fields: " + ", ".join(missing))
    if unexpected:
        details.append("unexpected fields: " + ", ".join(unexpected))
    raise ProtocolError("invalid_fields", "; ".join(details))
