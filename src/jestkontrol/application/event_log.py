"""A short history of what happened ("Sol tık", "Duraklatıldı"...) stored as translatable keys."""

import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from jestkontrol.application.frame_processor import FrameResult
from jestkontrol.application.ports import Frame
from jestkontrol.application.system_controller import SystemStatus
from jestkontrol.domain.gestures import Clicked, DragStarted, GestureEvent, MouseButton
from jestkontrol.domain.modes import SystemState

MAX_EVENTS = 50


@dataclass(frozen=True, slots=True)
class LoggedEvent:
    at: datetime
    key: str
    params: dict[str, str] = field(default_factory=dict)


class EventLog:
    def __init__(self, now: Callable[[], datetime] = datetime.now) -> None:
        self._now = now
        self._lock = threading.Lock()
        self._events: deque[LoggedEvent] = deque(maxlen=MAX_EVENTS)

    def add(self, key: str, **params: str) -> None:
        with self._lock:
            self._events.append(LoggedEvent(self._now(), key, params))

    def recent(self, count: int) -> list[LoggedEvent]:
        """Newest first."""
        with self._lock:
            return list(self._events)[-count:][::-1]


_GESTURE_EVENT_KEYS: dict[GestureEvent, str] = {
    Clicked(MouseButton.LEFT): "event.left_click",
    Clicked(MouseButton.RIGHT): "event.right_click",
    DragStarted(): "event.drag",
}


class EventRecorder:
    """Feeds the EventLog from frame results and system status changes."""

    def __init__(self, log: EventLog) -> None:
        self._log = log
        self._last_state = SystemState.OFF

    def on_frame(self, _: Frame, result: FrameResult) -> None:
        for event in result.events:
            key = _GESTURE_EVENT_KEYS.get(event)
            if key is not None:
                self._log.add(key)

    def on_status(self, status: SystemStatus) -> None:
        previous, self._last_state = self._last_state, status.state
        if status.state is previous:
            self._log.add("event.mode", mode=f"mode.{status.mode.value}")
        elif status.state is SystemState.ACTIVE:
            self._log.add("event.resumed" if previous is SystemState.PAUSED else "event.started")
        elif status.state is SystemState.PAUSED:
            self._log.add("event.paused")
        else:
            self._log.add("event.stopped")
