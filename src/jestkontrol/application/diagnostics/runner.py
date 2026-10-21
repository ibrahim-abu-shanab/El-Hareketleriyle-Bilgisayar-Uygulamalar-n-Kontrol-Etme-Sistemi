"""Runs one diagnostic at a time against the live camera pipeline and records its result."""

import threading
from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from jestkontrol.application.diagnostics.accuracy_test import AccuracyGesture, AccuracyTestSession
from jestkontrol.application.diagnostics.fps_test import FpsTestSession
from jestkontrol.application.diagnostics.history import DiagnosticsHistory
from jestkontrol.application.diagnostics.records import accuracy_record, fps_record
from jestkontrol.application.frame_processor import FrameResult
from jestkontrol.application.observable import Listeners, Unsubscribe
from jestkontrol.application.ports import Clock, Frame, SettingsProvider
from jestkontrol.application.system_controller import SystemController
from jestkontrol.domain.gestures import Clicked
from jestkontrol.domain.modes import OperatingMode, SystemState


class SystemStarter(Protocol):
    def start(self) -> None:
        """Start the camera pipeline; a no-op when it already runs."""


class DiagnosticsRunner:
    def __init__(
        self,
        starter: SystemStarter,
        controller: SystemController,
        settings: SettingsProvider,
        history: DiagnosticsHistory,
        clock: Clock,
        now: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._starter = starter
        self._controller = controller
        self._settings = settings
        self._history = history
        self._clock = clock
        self._now = now
        self._lock = threading.Lock()
        self._fps: FpsTestSession | None = None
        self._accuracy: AccuracyTestSession | None = None
        self._finished_listeners = Listeners()

    @property
    def fps_session(self) -> FpsTestSession | None:
        return self._fps

    @property
    def accuracy_session(self) -> AccuracyTestSession | None:
        return self._accuracy

    @property
    def is_running(self) -> bool:
        return self._fps is not None or self._accuracy is not None

    def on_finished(self, listener: Callable[[], None]) -> Unsubscribe:
        return self._finished_listeners.add(listener)

    def start_fps_test(self, duration_s: int) -> None:
        """Raises CameraError if the camera cannot be started."""
        with self._lock:
            self._accuracy = None
            self._fps = FpsTestSession(duration_s)
        self._start_system()

    def start_accuracy_test(self, gesture: AccuracyGesture, trials: int) -> None:
        """Raises CameraError if the camera cannot be started."""
        session = AccuracyTestSession(gesture, trials)
        with self._lock:
            self._fps = None
            self._accuracy = session
        self._start_system()
        self._controller.set_mode(OperatingMode.MOUSE)
        if self._controller.state is SystemState.PAUSED:
            self._controller.resume()
        session.start(self._clock.now())  # the first trial's clock starts once the camera is live

    def _start_system(self) -> None:
        """The session is registered first, so a camera that dies at once still cancels it."""
        try:
            self._starter.start()
        except Exception:
            self.cancel()
            raise

    def cancel(self) -> None:
        with self._lock:
            self._fps = None
            self._accuracy = None

    def on_frame(self, _: Frame, result: FrameResult) -> None:
        now = self._clock.now()
        if (fps := self._fps) is not None:
            self._feed_fps(fps, now)
        elif (accuracy := self._accuracy) is not None:
            self._feed_accuracy(accuracy, result, now)

    def _feed_fps(self, session: FpsTestSession, now: float) -> None:
        session.on_frame(now)
        if session.is_finished(now):
            with self._lock:
                self._fps = None
            self._history.add(fps_record(session.result(), self._settings.current, self._now()))
            self._notify_finished()

    def _feed_accuracy(self, session: AccuracyTestSession, result: FrameResult, now: float) -> None:
        for event in result.events:
            if isinstance(event, Clicked):
                session.on_click(event.button, now)
        session.tick(now)
        if session.is_finished:
            with self._lock:
                self._accuracy = None
            self._history.add(accuracy_record(session.result(), self._now()))
            self._notify_finished()

    def _notify_finished(self) -> None:
        self._finished_listeners.notify()
