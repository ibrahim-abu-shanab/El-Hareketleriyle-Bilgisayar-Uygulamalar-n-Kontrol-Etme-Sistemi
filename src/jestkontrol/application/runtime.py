"""Owns the capture loop thread and the start / stop lifecycle of the system."""

import logging
import threading
from collections.abc import Callable

from jestkontrol.application.frame_processor import FrameProcessor, FrameResult
from jestkontrol.application.metrics import PerformanceMeter
from jestkontrol.application.observable import Listeners, Unsubscribe
from jestkontrol.application.ports import CameraError, Clock, Frame, FrameSource
from jestkontrol.application.system_controller import SystemController
from jestkontrol.domain.modes import SystemState

logger = logging.getLogger(__name__)

FrameListener = Callable[[Frame, FrameResult], None]
ErrorListener = Callable[[Exception], None]
_JOIN_TIMEOUT_S = 2.0


class GestureRuntime:
    def __init__(
        self,
        source: FrameSource,
        processor: FrameProcessor,
        controller: SystemController,
        meter: PerformanceMeter,
        clock: Clock,
    ) -> None:
        self._source = source
        self._processor = processor
        self._controller = controller
        self._meter = meter
        self._clock = clock
        self._lifecycle_lock = threading.Lock()
        self._stop_requested = threading.Event()
        self._thread: threading.Thread | None = None
        self._frame_listeners = Listeners()
        self._error_listeners = Listeners()

    def add_frame_listener(self, listener: FrameListener) -> Unsubscribe:
        return self._frame_listeners.add(listener)

    def add_error_listener(self, listener: ErrorListener) -> Unsubscribe:
        return self._error_listeners.add(listener)

    def start(self) -> None:
        """Open the camera and begin processing; raises CameraError if it cannot be opened."""
        self._wait_for_previous_session()
        with self._lifecycle_lock:
            if self._thread is not None:
                return
            self._source.open()
            self._meter.reset()
            self._stop_requested.clear()
            self._controller.start()
            self._thread = threading.Thread(target=self._run, name="gesture-loop", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Turns the system OFF at once; the camera is released as soon as the current read returns."""
        with self._lifecycle_lock:
            thread = self._thread
            if thread is None:
                return
            self._stop_requested.set()
        self._controller.stop()
        if thread is not threading.current_thread():
            thread.join(_JOIN_TIMEOUT_S)

    def toggle_running(self) -> None:
        if self._controller.state is SystemState.OFF:
            self.start()
        else:
            self.stop()

    def _wait_for_previous_session(self) -> None:
        with self._lifecycle_lock:
            closing = self._thread if self._stop_requested.is_set() else None
        if closing is None:
            return
        closing.join(_JOIN_TIMEOUT_S)
        if closing.is_alive():
            raise CameraError("The previous camera session is still closing")

    def _run(self) -> None:
        try:
            self._process_frames()
        except Exception as error:  # thread boundary: any failure must end in the safe OFF state
            logger.exception("Gesture loop stopped by an error")
            self._error_listeners.notify(error)
        finally:
            self._shutdown()

    def _process_frames(self) -> None:
        while not self._stop_requested.is_set():
            started_at = self._clock.now()
            frame = self._source.read()
            if self._stop_requested.is_set():
                break
            result = self._processor.process(frame)
            self._meter.record(started_at, self._clock.now())
            self._frame_listeners.notify(frame, result)

    def _shutdown(self) -> None:
        try:
            self._processor.release()
        finally:
            self._source.close()
            self._controller.stop()
            with self._lifecycle_lock:
                self._thread = None
                self._stop_requested.clear()
