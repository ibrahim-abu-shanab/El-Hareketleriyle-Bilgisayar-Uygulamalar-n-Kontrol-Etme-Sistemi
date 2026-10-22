"""Latest camera frame and recognition state, shared between the capture thread and the UI."""

import threading
from dataclasses import dataclass

from jestkontrol.application.frame_processor import FrameResult
from jestkontrol.application.gesture_catalog import gesture_of
from jestkontrol.application.ports import Clock, Frame
from jestkontrol.domain.gestures import GestureType
from jestkontrol.domain.landmarks import HandFrame

# A discrete gesture (click, drag...) stays on display this long after it fired.
GESTURE_HOLD_S = 0.8


@dataclass(frozen=True, slots=True)
class LiveSnapshot:
    frame: Frame | None = None
    hand: HandFrame | None = None
    gesture: GestureType | None = None


class LiveMonitor:
    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._snapshot = LiveSnapshot()
        self._held: tuple[GestureType, float] | None = None  # (gesture, expires_at)

    def on_frame(self, frame: Frame, result: FrameResult) -> None:
        now = self._clock.now()
        self._remember_discrete_gesture(result, now)
        gesture = self._held[0] if self._held and self._held[1] > now else self._continuous(result)
        snapshot = LiveSnapshot(frame, result.hand, gesture)
        with self._lock:
            self._snapshot = snapshot

    def snapshot(self) -> LiveSnapshot:
        with self._lock:
            return self._snapshot

    def clear(self) -> None:
        with self._lock:
            self._snapshot = LiveSnapshot()
        self._held = None

    def _remember_discrete_gesture(self, result: FrameResult, now: float) -> None:
        for event in result.events:
            gesture = gesture_of(event)
            if gesture not in (None, GestureType.MOVE):
                self._held = (gesture, now + GESTURE_HOLD_S)

    @staticmethod
    def _continuous(result: FrameResult) -> GestureType | None:
        for event in result.events:
            if gesture_of(event) is GestureType.MOVE:
                return GestureType.MOVE
        return None
