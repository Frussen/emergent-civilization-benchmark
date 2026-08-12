"""Framework-independent controller over the canonical simulation."""

from __future__ import annotations

from enum import StrEnum

from ecb.simulation import Simulation
from ecb.visual.snapshot import VisualSnapshot


class VisualSpeed(StrEnum):
    """Presentation pacing choices; these have no scientific meaning."""

    ONE_X = "1x"
    FIVE_X = "5x"
    TWENTY_X = "20x"
    MAX = "max"


class VisualController:
    """Observe and drive one already-constructed authoritative simulation.

    M1.0a has no scheduler: playing and speed are presentation state only.
    ``step`` delegates even after extinction because canonical ``Simulation.step``
    remains legal. The visual runtime's automatic scheduler detects extinction and
    pauses its own loop. Concurrent server code must also serialize calls to
    ``advance``, ``step``, and ``current_snapshot`` through one synchronization
    boundary; the visual runtime supplies that boundary.
    """

    __slots__ = ("_is_playing", "_simulation", "_speed")

    def __init__(self, simulation: Simulation) -> None:
        if not isinstance(simulation, Simulation):
            raise TypeError("simulation must be a Simulation")
        self._simulation = simulation
        self._is_playing = False
        self._speed = VisualSpeed.ONE_X

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def speed(self) -> VisualSpeed:
        return self._speed

    @property
    def tick(self) -> int:
        """Return the current canonical simulation tick."""
        return self._simulation.world.tick

    @property
    def is_extinct(self) -> bool:
        """Return whether the authoritative population has no living agents."""
        return not any(agent.alive for agent in self._simulation.world.agents.values())

    def current_snapshot(self) -> VisualSnapshot:
        """Return a pure projection of the current authoritative state."""
        return VisualSnapshot.from_simulation(self._simulation)

    def step(self) -> VisualSnapshot:
        """Execute exactly one canonical simulation tick and snapshot its result."""
        self.advance()
        return self.current_snapshot()

    def advance(self) -> None:
        """Execute exactly one canonical tick without constructing a snapshot."""
        self._simulation.step()

    def play(self) -> None:
        """Enable future scheduler-driven advancement without advancing now."""
        self._is_playing = True

    def pause(self) -> None:
        """Disable future scheduler-driven advancement without advancing now."""
        self._is_playing = False

    def set_speed(self, speed: VisualSpeed) -> None:
        """Set presentation pacing without changing scientific state."""
        if not isinstance(speed, VisualSpeed):
            raise TypeError("speed must be a VisualSpeed")
        self._speed = speed
