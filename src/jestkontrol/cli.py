"""Command line entry: opens the GUI, or with --headless runs without a window."""

import argparse
import logging
import threading
from collections.abc import Sequence

from jestkontrol.application.frame_processor import FrameResult
from jestkontrol.application.metrics import PerformanceMeter
from jestkontrol.application.ports import CameraError, Clock, Frame
from jestkontrol.application.services import AppServices
from jestkontrol.bootstrap import create_application
from jestkontrol.domain.gestures import CursorMoved, GestureEvent
from jestkontrol.domain.modes import OperatingMode, SystemState
from jestkontrol.ui.app import run_gui

REPORT_INTERVAL_S = 0.5


class ConsoleReporter:
    """Prints FPS, latency, hand presence and recent gestures a couple of times per second."""

    def __init__(self, meter: PerformanceMeter, clock: Clock) -> None:
        self._meter = meter
        self._clock = clock
        self._last_report_at = 0.0
        self._recent_events: list[str] = []

    def on_frame(self, _: Frame, result: FrameResult) -> None:
        self._recent_events.extend(
            type(event).__name__ for event in result.events if _is_noteworthy(event)
        )
        now = self._clock.now()
        if now - self._last_report_at < REPORT_INTERVAL_S:
            return
        self._last_report_at = now
        snapshot = self._meter.snapshot()
        hand = "hand" if result.hand else "no hand"
        events = ", ".join(self._recent_events) or "-"
        print(f"{snapshot.fps:5.1f} FPS | {snapshot.latency_ms:5.1f} ms | {hand:7} | {events}")
        self._recent_events.clear()


def _is_noteworthy(event: GestureEvent) -> bool:
    return not isinstance(event, CursorMoved)


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="jestkontrol", description="Hand-gesture computer control")
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in OperatingMode],
        default=OperatingMode.MOUSE.value,
        help="operating mode for --headless (default: mouse)",
    )
    parser.add_argument("--headless", action="store_true", help="run without the window (console only)")
    parser.add_argument("--debug", action="store_true", help="print live FPS/latency/gestures (headless)")
    return parser.parse_args(argv)


def run(app: AppServices, mode: OperatingMode, debug: bool) -> int:
    app.controller.set_mode(mode)
    stopped = threading.Event()
    app.controller.subscribe(
        lambda status: stopped.set() if status.state is SystemState.OFF else None
    )
    app.runtime.add_error_listener(lambda error: print(f"Stopped: {error}"))
    if debug:
        app.runtime.add_frame_listener(ConsoleReporter(app.meter, app.clock).on_frame)
    try:
        app.emergency.activate(app.runtime.toggle_running)
        hotkey_note = f"{app.emergency.current} stops"
    except OSError as error:
        hotkey_note = f"emergency hotkey unavailable ({error}); Ctrl+C stops"
    try:
        app.runtime.start()
    except CameraError as error:
        print(f"Cannot start: {error}")
        return 1
    print(f"JestKontrol running in {mode.value} mode - {hotkey_note}.")
    stopped.wait()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING)
    app = create_application()
    try:
        if not args.headless:
            return run_gui(app)
        return run(app, OperatingMode(args.mode), args.debug)
    except KeyboardInterrupt:
        return 0
    finally:
        app.shutdown()
