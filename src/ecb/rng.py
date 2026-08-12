"""The sole random-number interface used by the M0 implementation."""

from __future__ import annotations

import random
from collections.abc import MutableSequence, Sequence
from typing import TypeVar

T = TypeVar("T")


class SeededRNG:
    """A deliberately small project-controlled wrapper around a seeded PRNG."""

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self._random = random.Random(seed)

    def randint(self, start: int, stop: int) -> int:
        return self._random.randint(start, stop)

    def choice(self, values: Sequence[T]) -> T:
        return self._random.choice(values)

    def shuffle(self, values: MutableSequence[T]) -> None:
        self._random.shuffle(values)

    def state(self) -> tuple[object, ...]:
        """Return the complete deterministic continuation state."""
        return self._random.getstate()

    def restore(self, state: tuple[object, ...]) -> None:
        self._random.setstate(state)
