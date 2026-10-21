"""Notices when the system is running but no hand has been visible for a while."""

from collections.abc import Callable

from jestkontrol.application.frame_processor import FrameResult
from jestkontrol.application.observable import Listeners, Unsubscribe
from jestkontrol.application.ports import Clock, Frame
from jestkontrol.application.system_controller import SystemController
from jestkontrol.domain.modes import SystemState

NO_HAND_NOTICE_AFTER_S = 3.0


class HandPresenceMonitor:
    def __init__(self, clock: Clock, controller: SystemController) -> None:
        self._clock = clock
        self._controller = controller
        self._listeners = Listeners()
        self._missing_since: float | None = None
        self._notified = False

    def subscribe(self, listener: Callable[[], None]) -> Unsubscribe:
        """``listener`` is called once per absence (on the capture thread)."""
        return self._listeners.add(listener)

    def on_frame(self, _: Frame, result: FrameResult) -> None:
        if result.hand is not None or self._controller.state is not SystemState.ACTIVE:
            self._missing_since = None
            self._notified = False
            return
        now = self._clock.now()
        if self._missing_since is None:
            self._missing_since = now
        if not self._notified and now - self._missing_since >= NO_HAND_NOTICE_AFTER_S:
            self._notified = True
            self._listeners.notify()
