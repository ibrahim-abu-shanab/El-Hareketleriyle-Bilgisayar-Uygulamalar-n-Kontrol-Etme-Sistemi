"""Exponential smoothing of a scalar signal (removes jitter)."""


class ExponentialSmoother:
    def __init__(self) -> None:
        self._last: float | None = None

    def smooth(self, target: float, alpha: float) -> float:
        """alpha is the weight of ``target``; alpha=1 passes it through unchanged."""
        if self._last is None:
            self._last = target
        else:
            self._last += alpha * (target - self._last)
        return self._last

    def reset(self) -> None:
        self._last = None
