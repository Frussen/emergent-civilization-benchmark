"""Synchronized asyncio runtime for one authoritative visual session."""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite

from ecb.visual.controller import VisualController, VisualSpeed
from ecb.visual.protocol import (
    ClientCommand,
    EncodedServerMessage,
    PauseCommand,
    PlayCommand,
    ProtocolError,
    ServerMessage,
    SetSpeedCommand,
    StepCommand,
    encode_server_message,
    error_message,
    server_error_message,
    snapshot_message,
    status_message,
)
from ecb.visual.snapshot import VisualSnapshot

TICKS_PER_SECOND = {
    VisualSpeed.ONE_X: 1,
    VisualSpeed.FIVE_X: 5,
    VisualSpeed.TWENTY_X: 20,
}
DEFAULT_MAX_SNAPSHOT_RATE = 25.0


class SubscriptionClosed(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class _MailboxItem:
    sequence: int
    text: EncodedServerMessage


class VisualSubscription:
    """Bounded non-blocking mailbox with reliable control and latest-only frames.

    All mutation occurs synchronously on the owning asyncio event loop. A full
    reliable mailbox closes the subscription instead of blocking a publisher.
    """

    __slots__ = (
        "_close_reason",
        "_close_callbacks",
        "_closed",
        "_latest_snapshot",
        "_ready",
        "_reliable",
        "_reliable_limit",
    )

    def __init__(self, reliable_limit: int) -> None:
        self._closed = False
        self._close_reason = "visual subscription is closed"
        self._close_callbacks: set[Callable[[], None]] = set()
        self._ready = asyncio.Event()
        self._latest_snapshot: _MailboxItem | None = None
        self._reliable: deque[_MailboxItem] = deque()
        self._reliable_limit = reliable_limit

    @property
    def is_closed(self) -> bool:
        return self._closed

    @property
    def pending_snapshot_count(self) -> int:
        return int(self._latest_snapshot is not None)

    @property
    def pending_reliable_count(self) -> int:
        return len(self._reliable)

    def publish_snapshot(self, sequence: int, text: EncodedServerMessage) -> bool:
        """Replace an unconsumed frame without waiting for a consumer."""
        if self._closed:
            return False
        item = _MailboxItem(sequence, text)
        if self._latest_snapshot is not None:
            if sequence < self._latest_snapshot.sequence:
                return True
            # Retain the original ordering position while replacing its payload.
            item = _MailboxItem(self._latest_snapshot.sequence, text)
        self._latest_snapshot = item
        self._ready.set()
        return True

    def publish_reliable(self, sequence: int, text: EncodedServerMessage) -> bool:
        """Enqueue without waiting, closing this client on bounded overload."""
        if self._closed:
            return False
        if len(self._reliable) >= self._reliable_limit:
            self.close("reliable visual mailbox capacity exceeded")
            return False
        self._reliable.append(_MailboxItem(sequence, text))
        self._ready.set()
        return True

    async def receive_text(self) -> EncodedServerMessage:
        while True:
            if self._closed:
                raise SubscriptionClosed(self._close_reason)
            item = self._pop_next()
            if item is not None:
                return item.text
            self._ready.clear()
            await self._ready.wait()

    def add_close_callback(self, callback: Callable[[], None]) -> None:
        if self._closed:
            callback()
            return
        self._close_callbacks.add(callback)

    def remove_close_callback(self, callback: Callable[[], None]) -> None:
        self._close_callbacks.discard(callback)

    def close(self, reason: str = "visual subscription is closed") -> None:
        if self._closed:
            return
        self._closed = True
        self._close_reason = reason
        self._latest_snapshot = None
        self._reliable.clear()
        self._ready.set()
        for callback in tuple(self._close_callbacks):
            callback()
        self._close_callbacks.clear()

    def _pop_next(self) -> _MailboxItem | None:
        reliable = self._reliable[0] if self._reliable else None
        snapshot = self._latest_snapshot
        if snapshot is not None and (
            reliable is None or snapshot.sequence <= reliable.sequence
        ):
            self._latest_snapshot = None
            return snapshot
        if reliable is not None:
            return self._reliable.popleft()
        return None


@dataclass(frozen=True, slots=True)
class RuntimeStatus:
    playing: bool
    speed: VisualSpeed
    extinct: bool
    tick: int
    scheduler_error: str | None = None

    def to_message(self) -> ServerMessage:
        return status_message(
            playing=self.playing,
            speed=self.speed,
            extinct=self.extinct,
            tick=self.tick,
            scheduler_error=self.scheduler_error,
        )


def next_pacing_deadline(
    previous_deadline: float, now: float, interval: float
) -> float:
    """Advance one deadline without accumulating an unbounded catch-up debt."""
    return max(previous_deadline + interval, now)


class VisualRuntime:
    """Own scheduling and synchronized access to one VisualController.

    ``_access_lock`` covers only authoritative controller access and snapshot
    capture. Encoding and bounded, non-blocking mailbox publication occur after
    that lock is released. ``_publication_lock`` preserves causal message order
    without extending the scientific critical section to transport work.
    """

    __slots__ = (
        "_access_lock",
        "_closed",
        "_controller",
        "_max_snapshot_interval",
        "_publication_lock",
        "_publication_sequence",
        "_reliable_queue_limit",
        "_scheduler_error",
        "_scheduler_task",
        "_state_changed",
        "_subscriptions",
    )

    def __init__(
        self,
        controller: VisualController,
        *,
        reliable_queue_limit: int = 32,
        max_snapshot_rate: int | float = DEFAULT_MAX_SNAPSHOT_RATE,
    ) -> None:
        if not isinstance(controller, VisualController):
            raise TypeError("controller must be a VisualController")
        if type(reliable_queue_limit) is not int or reliable_queue_limit < 2:
            raise ValueError("reliable_queue_limit must be an integer of at least 2")
        if type(max_snapshot_rate) not in {int, float}:
            raise TypeError("max_snapshot_rate must be a built-in int or float")
        if not isfinite(max_snapshot_rate) or max_snapshot_rate <= 0:
            raise ValueError("max_snapshot_rate must be positive and finite")
        self._controller = controller
        self._access_lock = asyncio.Lock()
        self._publication_lock = asyncio.Lock()
        self._state_changed = asyncio.Event()
        self._subscriptions: set[VisualSubscription] = set()
        self._reliable_queue_limit = reliable_queue_limit
        self._max_snapshot_interval = 1.0 / max_snapshot_rate
        self._publication_sequence = 0
        self._scheduler_task: asyncio.Task[None] | None = None
        self._scheduler_error: str | None = None
        self._closed = False

    @property
    def connection_count(self) -> int:
        return len(self._subscriptions)

    @property
    def scheduler_task(self) -> asyncio.Task[None] | None:
        return self._scheduler_task

    async def start(self) -> None:
        async with self._access_lock:
            self._require_open_locked()
            if self._scheduler_task is not None:
                return
            self._scheduler_error = None
            self._scheduler_task = asyncio.create_task(
                self._scheduler_loop(), name="ecb-visual-scheduler"
            )

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._state_changed.set()
        subscriptions = tuple(self._subscriptions)
        for subscription in subscriptions:
            subscription.close("visual runtime is closed")
        scheduler_task = self._scheduler_task
        if scheduler_task is not None:
            scheduler_task.cancel()
            await asyncio.gather(scheduler_task, return_exceptions=True)
        async with self._publication_lock:
            async with self._access_lock:
                self._subscriptions.clear()
                self._scheduler_task = None

    async def register(self) -> VisualSubscription:
        async with self._publication_lock:
            subscription = VisualSubscription(self._reliable_queue_limit)
            async with self._access_lock:
                self._require_open_locked()
                self._subscriptions.add(subscription)
                snapshot = self._controller.current_snapshot()
                status = self._status_locked()
                snapshot_sequence, status_sequence = self._reserve_sequences(2)
            snapshot_text = encode_server_message(snapshot_message(snapshot))
            status_text = encode_server_message(status.to_message())
            subscription.publish_snapshot(snapshot_sequence, snapshot_text)
            subscription.publish_reliable(status_sequence, status_text)
            return subscription

    async def unregister(self, subscription: VisualSubscription) -> None:
        async with self._access_lock:
            self._subscriptions.discard(subscription)
        subscription.close()

    async def current_snapshot(self) -> VisualSnapshot:
        async with self._access_lock:
            self._require_open_locked()
            return self._controller.current_snapshot()

    async def status(self) -> RuntimeStatus:
        async with self._access_lock:
            self._require_open_locked()
            return self._status_locked()

    async def play(self) -> RuntimeStatus:
        async with self._publication_lock:
            async with self._access_lock:
                self._require_open_locked()
                if self._controller.is_extinct:
                    self._controller.pause()
                else:
                    self._scheduler_error = None
                    self._controller.play()
                status = self._status_locked()
                sequence = self._reserve_sequences(1)[0]
                subscriptions = tuple(self._subscriptions)
            self._state_changed.set()
            await self._publish_reliable(
                subscriptions,
                sequence,
                encode_server_message(status.to_message()),
            )
            return status

    async def pause(self) -> RuntimeStatus:
        async with self._publication_lock:
            async with self._access_lock:
                self._require_open_locked()
                self._controller.pause()
                status = self._status_locked()
                sequence = self._reserve_sequences(1)[0]
                subscriptions = tuple(self._subscriptions)
            self._state_changed.set()
            await self._publish_reliable(
                subscriptions,
                sequence,
                encode_server_message(status.to_message()),
            )
            return status

    async def set_speed(self, speed: VisualSpeed) -> RuntimeStatus:
        async with self._publication_lock:
            async with self._access_lock:
                self._require_open_locked()
                self._controller.set_speed(speed)
                status = self._status_locked()
                sequence = self._reserve_sequences(1)[0]
                subscriptions = tuple(self._subscriptions)
            self._state_changed.set()
            await self._publish_reliable(
                subscriptions,
                sequence,
                encode_server_message(status.to_message()),
            )
            return status

    async def step(self) -> VisualSnapshot:
        """Perform one explicit canonical step, including after extinction."""
        async with self._publication_lock:
            async with self._access_lock:
                self._require_open_locked()
                self._controller_advance()
                snapshot = self._controller.current_snapshot()
                status = self._status_locked()
                snapshot_sequence, status_sequence = self._reserve_sequences(2)
                subscriptions = tuple(self._subscriptions)
            snapshot_text = encode_server_message(snapshot_message(snapshot))
            status_text = encode_server_message(status.to_message())
            rejected = self._publish_snapshot(
                subscriptions, snapshot_sequence, snapshot_text
            )
            rejected.update(
                self._publish_reliable_now(subscriptions, status_sequence, status_text)
            )
            await self._prune_subscriptions(rejected)
            return snapshot

    async def advance_scheduled_once(
        self,
        *,
        expected_speed: VisualSpeed | None = None,
        publish_snapshot: bool = True,
    ) -> VisualSnapshot | None:
        """Execute one automatic tick, optionally omitting its visual frame."""
        async with self._publication_lock:
            async with self._access_lock:
                self._require_open_locked()
                if not self._controller.is_playing:
                    return None
                if (
                    expected_speed is not None
                    and self._controller.speed is not expected_speed
                ):
                    return None

                already_extinct = self._controller.is_extinct
                if not already_extinct:
                    self._controller_advance()
                extinct = self._controller.is_extinct
                if extinct:
                    self._controller.pause()

                snapshot = (
                    self._controller.current_snapshot()
                    if publish_snapshot or extinct
                    else None
                )
                status = self._status_locked() if extinct else None
                sequence_count = int(snapshot is not None) + int(status is not None)
                sequences = self._reserve_sequences(sequence_count)
                subscriptions = tuple(self._subscriptions)

            rejected: set[VisualSubscription] = set()
            sequence_index = 0
            if snapshot is not None:
                snapshot_text = encode_server_message(snapshot_message(snapshot))
                rejected.update(
                    self._publish_snapshot(
                        subscriptions, sequences[sequence_index], snapshot_text
                    )
                )
                sequence_index += 1
            if status is not None:
                status_text = encode_server_message(status.to_message())
                rejected.update(
                    self._publish_reliable_now(
                        subscriptions, sequences[sequence_index], status_text
                    )
                )
                self._state_changed.set()
            await self._prune_subscriptions(rejected)
            return None if already_extinct else snapshot

    async def publish_protocol_error(
        self, subscription: VisualSubscription, error: ProtocolError
    ) -> None:
        async with self._publication_lock:
            async with self._access_lock:
                self._require_open_locked()
                sequence = self._reserve_sequences(1)[0]
            accepted = subscription.publish_reliable(
                sequence, encode_server_message(error_message(error))
            )
            if not accepted:
                await self._prune_subscriptions({subscription})

    async def handle_command(self, command: ClientCommand) -> None:
        if type(command) is PlayCommand:
            await self.play()
        elif type(command) is PauseCommand:
            await self.pause()
        elif type(command) is StepCommand:
            await self.step()
        elif type(command) is SetSpeedCommand:
            await self.set_speed(command.speed)
        else:
            raise TypeError(f"unsupported command type: {type(command)!r}")

    def _controller_advance(self) -> None:
        """Advance canonically while the authoritative runtime lock is held."""
        self._controller.advance()

    async def _scheduler_loop(self) -> None:
        try:
            while True:
                try:
                    await self._run_scheduler()
                except Exception as error:
                    await self._handle_scheduler_failure(error)
        except asyncio.CancelledError:
            raise
        finally:
            if self._scheduler_task is asyncio.current_task():
                self._scheduler_task = None

    async def _run_scheduler(self) -> None:
        finite_deadline: float | None = None
        finite_speed: VisualSpeed | None = None
        max_publication_deadline: float | None = None
        loop = asyncio.get_running_loop()

        while True:
            self._state_changed.clear()
            playing, speed = await self._playback_state()
            if not playing:
                finite_deadline = None
                finite_speed = None
                max_publication_deadline = None
                await self._state_changed.wait()
                continue

            if speed is VisualSpeed.MAX:
                finite_deadline = None
                finite_speed = None
                now = loop.time()
                publish = (
                    max_publication_deadline is None or now >= max_publication_deadline
                )
                await self.advance_scheduled_once(
                    expected_speed=speed, publish_snapshot=publish
                )
                if publish:
                    max_publication_deadline = loop.time() + self._max_snapshot_interval
                await asyncio.sleep(0)
                continue

            max_publication_deadline = None
            interval = 1.0 / TICKS_PER_SECOND[speed]
            now = loop.time()
            if finite_deadline is None or finite_speed is not speed:
                finite_deadline = now + interval
                finite_speed = speed
            delay = max(0.0, finite_deadline - now)
            try:
                await asyncio.wait_for(self._state_changed.wait(), timeout=delay)
            except TimeoutError:
                await self.advance_scheduled_once(expected_speed=speed)
                finite_deadline = next_pacing_deadline(
                    finite_deadline, loop.time(), interval
                )
            await asyncio.sleep(0)

    async def _handle_scheduler_failure(self, error: Exception) -> None:
        detail = f"{type(error).__name__}: {error}"
        async with self._publication_lock:
            async with self._access_lock:
                if self._closed:
                    return
                self._controller.pause()
                self._scheduler_error = detail
                status = self._status_locked()
                error_sequence, status_sequence = self._reserve_sequences(2)
                subscriptions = tuple(self._subscriptions)
            rejected = self._publish_reliable_now(
                subscriptions,
                error_sequence,
                encode_server_message(
                    server_error_message(code="scheduler_error", message=detail)
                ),
            )
            rejected.update(
                self._publish_reliable_now(
                    subscriptions,
                    status_sequence,
                    encode_server_message(status.to_message()),
                )
            )
            await self._prune_subscriptions(rejected)
            self._state_changed.set()

    async def _playback_state(self) -> tuple[bool, VisualSpeed]:
        async with self._access_lock:
            self._require_open_locked()
            return self._controller.is_playing, self._controller.speed

    def _status_locked(self) -> RuntimeStatus:
        return RuntimeStatus(
            playing=self._controller.is_playing,
            speed=self._controller.speed,
            extinct=self._controller.is_extinct,
            tick=self._controller.tick,
            scheduler_error=self._scheduler_error,
        )

    def _reserve_sequences(self, count: int) -> tuple[int, ...]:
        first = self._publication_sequence + 1
        self._publication_sequence += count
        return tuple(range(first, first + count))

    @staticmethod
    def _publish_snapshot(
        subscriptions: tuple[VisualSubscription, ...],
        sequence: int,
        text: EncodedServerMessage,
    ) -> set[VisualSubscription]:
        return {
            subscription
            for subscription in subscriptions
            if not subscription.publish_snapshot(sequence, text)
        }

    @staticmethod
    def _publish_reliable_now(
        subscriptions: tuple[VisualSubscription, ...],
        sequence: int,
        text: EncodedServerMessage,
    ) -> set[VisualSubscription]:
        return {
            subscription
            for subscription in subscriptions
            if not subscription.publish_reliable(sequence, text)
        }

    async def _publish_reliable(
        self,
        subscriptions: tuple[VisualSubscription, ...],
        sequence: int,
        text: EncodedServerMessage,
    ) -> None:
        await self._prune_subscriptions(
            self._publish_reliable_now(subscriptions, sequence, text)
        )

    async def _prune_subscriptions(self, rejected: set[VisualSubscription]) -> None:
        if not rejected:
            return
        async with self._access_lock:
            self._subscriptions.difference_update(rejected)

    def _require_open_locked(self) -> None:
        if self._closed:
            raise RuntimeError("visual runtime is closed")
