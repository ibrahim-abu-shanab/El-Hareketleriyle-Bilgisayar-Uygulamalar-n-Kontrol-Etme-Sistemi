"""Minimum interval between repeated discrete actions (prevents accidental double clicks)."""


class Cooldown:
    def __init__(self) -> None:
        self._last_fired_at: float | None = None

    def try_fire(self, now: float, period: float) -> bool:
        if self._last_fired_at is not None and now - self._last_fired_at < period:
            return False
        self._last_fired_at = now
        return True
