"""Local FastAPI transport for one shared ECB visual runtime."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from ecb.visual.protocol import ProtocolError, parse_client_message
from ecb.visual.runtime import VisualRuntime, VisualSubscription

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def create_app(runtime: VisualRuntime, *, start_scheduler: bool = True) -> FastAPI:
    """Create an isolated app around an already-constructed shared runtime."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if start_scheduler:
            await runtime.start()
        try:
            yield
        finally:
            await runtime.close()

    app = FastAPI(lifespan=lifespan)
    app.state.visual_runtime = runtime

    @app.get("/health")
    async def health() -> dict[str, object]:
        status = await runtime.status()
        return {
            "ok": True,
            "playing": status.playing,
            "speed": status.speed.value,
            "extinct": status.extinct,
            "tick": status.tick,
            "scheduler_error": status.scheduler_error,
        }

    @app.websocket("/ws")
    async def visual_socket(websocket: WebSocket) -> None:
        await websocket.accept()
        subscription = await runtime.register()
        sender = asyncio.create_task(
            _send_messages(websocket, subscription), name="ecb-visual-websocket-send"
        )
        connection_task = asyncio.current_task()

        def stop_receiver(_sender: asyncio.Task[None]) -> None:
            if connection_task is not None and not connection_task.done():
                connection_task.cancel()

        def stop_connection() -> None:
            sender.cancel()
            if connection_task is not None and not connection_task.done():
                connection_task.cancel()

        sender.add_done_callback(stop_receiver)
        subscription.add_close_callback(stop_connection)
        try:
            await _receive_commands(websocket, runtime, subscription)
        except WebSocketDisconnect:
            pass
        except asyncio.CancelledError:
            if not sender.done():
                raise
        finally:
            subscription.remove_close_callback(stop_connection)
            sender.remove_done_callback(stop_receiver)
            sender_finished = sender.done()
            sender.cancel()
            try:
                await asyncio.gather(sender, return_exceptions=True)
            finally:
                await runtime.unregister(subscription)
            if sender_finished:
                try:
                    await websocket.close()
                except RuntimeError:
                    pass

    return app


def run_server(
    runtime: VisualRuntime, *, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT
) -> None:
    """Run a supplied local visual session; loopback is the safe default."""
    uvicorn.run(create_app(runtime), host=host, port=port)


async def _send_messages(
    websocket: WebSocket, subscription: VisualSubscription
) -> None:
    while True:
        await websocket.send_text(await subscription.receive_text())


async def _receive_commands(
    websocket: WebSocket,
    runtime: VisualRuntime,
    subscription: VisualSubscription,
) -> None:
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            raise WebSocketDisconnect(
                code=message.get("code", 1000), reason=message.get("reason")
            )
        if message.get("bytes") is not None:
            await runtime.publish_protocol_error(
                subscription,
                ProtocolError(
                    "binary_not_supported", "visual protocol accepts text JSON only"
                ),
            )
            continue

        raw_message = message.get("text")
        if type(raw_message) is not str:
            await runtime.publish_protocol_error(
                subscription,
                ProtocolError("invalid_message", "message must contain text JSON"),
            )
            continue
        try:
            value = json.loads(raw_message)
        except json.JSONDecodeError:
            await runtime.publish_protocol_error(
                subscription,
                ProtocolError("invalid_json", "message must contain valid JSON"),
            )
            continue
        try:
            command = parse_client_message(value)
        except ProtocolError as error:
            await runtime.publish_protocol_error(subscription, error)
            continue
        await runtime.handle_command(command)
