"""FPS test (F10): counts processed frames per second over a fixed duration."""

from dataclasses import dataclass

TARGET_FPS = 25.0
DURATION_CHOICES_S = (10, 30, 60)
DEFAULT_DURATION_S = 30


@dataclass(frozen=True, slots=True)
class FpsTestResult:
    duration_s: int
    per_second: tuple[float, ...]

    @property
    def average(self) -> float:
        return sum(self.per_second) / len(self.per_second)

    @property
    def minimum(self) -> float:
        return min(self.per_second)

    @property
    def maximum(self) -> float:
        return max(self.per_second)

    @property
    def share_above_target(self) -> float:
        """Fraction of seconds that reached the target, in [0, 1]."""
        return sum(fps >= TARGET_FPS for fps in self.per_second) / len(self.per_second)

    @property
    def passed(self) -> bool:
        return self.average >= TARGET_FPS


class FpsTestSession:
    def __init__(self, duration_s: int = DEFAULT_DURATION_S) -> None:
        self.duration_s = duration_s
        self._started_at: float | None = None
        self._frames_per_second = [0] * duration_s

    def on_frame(self, now: float) -> None:
        if self._started_at is None:
            self._started_at = now
        second = int(now - self._started_at)
        if second < self.duration_s:
            self._frames_per_second[second] += 1

    def progress(self, now: float) -> float:
        """Completed share of the test in [0, 1]."""
        if self._started_at is None:
            return 0.0
        return min((now - self._started_at) / self.duration_s, 1.0)

    def is_finished(self, now: float) -> bool:
        return self.progress(now) >= 1.0

    def seconds_left(self, now: float) -> int:
        return round(self.duration_s * (1 - self.progress(now)))

    def result(self) -> FpsTestResult:
        return FpsTestResult(self.duration_s, tuple(float(n) for n in self._frames_per_second))
