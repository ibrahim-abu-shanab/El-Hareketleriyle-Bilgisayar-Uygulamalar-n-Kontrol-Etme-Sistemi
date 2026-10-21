"""Rolling FPS and per-frame latency measurement."""

import threading
from collections import deque
from dataclasses import dataclass

_MS_PER_S = 1000
DEFAULT_WINDOW = 30


@dataclass(frozen=True, slots=True)
class PerformanceSnapshot:
    fps: float
    latency_ms: float


class PerformanceMeter:
    def __init__(self, window: int = DEFAULT_WINDOW) -> None:
        self._lock = threading.Lock()
        self._finish_times: deque[float] = deque(maxlen=window)
        self._latencies: deque[float] = deque(maxlen=window)

    def record(self, started_at: float, finished_at: float) -> None:
        with self._lock:
            self._finish_times.append(finished_at)
            self._latencies.append(finished_at - started_at)

    def snapshot(self) -> PerformanceSnapshot:
        with self._lock:
            times = list(self._finish_times)
            latencies = list(self._latencies)
        return PerformanceSnapshot(_fps(times), _mean(latencies) * _MS_PER_S)

    def reset(self) -> None:
        with self._lock:
            self._finish_times.clear()
            self._latencies.clear()


def _fps(finish_times: list[float]) -> float:
    if len(finish_times) < 2:
        return 0.0
    elapsed = finish_times[-1] - finish_times[0]
    return (len(finish_times) - 1) / elapsed if elapsed > 0 else 0.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
