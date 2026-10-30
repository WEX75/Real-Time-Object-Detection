"""Injectable time source, so rules and events can be tested without sleeping."""

from __future__ import annotations

import time
from typing import Protocol


class Clock(Protocol):
    def now(self) -> float:
        """Seconds since the Unix epoch."""
        ...


class SystemClock:
    def now(self) -> float:
        return time.time()


class FakeClock:
    """Clock that only moves when a test tells it to."""

    def __init__(self, start: float = 1_800_000_000.0) -> None:
        self._now = start

    def now(self) -> float:
        return self._now

    def advance(self, seconds: float) -> float:
        if seconds < 0:
            raise ValueError("a clock cannot go backwards")
        self._now += seconds
        return self._now
