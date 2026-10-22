import threading

import pytest

from jestkontrol.application.actions import build_action_dispatcher
from jestkontrol.application.frame_processor import FrameProcessor
from jestkontrol.application.gesture_engine import GestureEngine
from jestkontrol.application.metrics import PerformanceMeter
from jestkontrol.application.ports import CameraError
from jestkontrol.application.recognizers.registry import create_default_recognizers
from jestkontrol.application.runtime import GestureRuntime
from jestkontrol.application.system_controller import SystemController
from jestkontrol.domain.modes import SystemState
from jestkontrol.domain.settings import Settings
from tests.fakes import (
    FakeClock,
    FakeFrameSource,
    FakeMouse,
    FakeScreen,
    FakeSettingsProvider,
    FakeTracker,
    FakeVolume,
)
from tests.hands import fist, open_hand

WAIT_S = 2.0


class Pipeline:
    def __init__(self, source=None, hands=None):
        self.mouse = FakeMouse()
        self.controller = SystemController()
        self.clock = FakeClock()
        self.source = source or FakeFrameSource()
        self.tracker = FakeTracker(hands)
        dispatcher = build_action_dispatcher(
            self.mouse, FakeScreen(), FakeVolume(), self.controller
        )
        self.processor = FrameProcessor(
            self.tracker,
            GestureEngine(create_default_recognizers()),
            dispatcher,
            self.controller,
            FakeSettingsProvider(Settings(smoothing_percent=0)),
            self.clock,
        )
        self.meter = PerformanceMeter()
        self.runtime = GestureRuntime(
            self.source, self.processor, self.controller, self.meter, self.clock
        )


def wait_until_off(controller: SystemController) -> None:
    stopped = threading.Event()
    controller.subscribe(lambda status: stopped.set() if status.state is SystemState.OFF else None)
    if controller.state is SystemState.OFF:
        stopped.set()
    assert stopped.wait(WAIT_S), "system did not reach the OFF state"


# --- FrameProcessor ----------------------------------------------------------------------------


def test_active_system_moves_the_mouse():
    pipeline = Pipeline(hands=[open_hand()])
    pipeline.controller.start()

    result = pipeline.processor.process(object())

    assert result.hand is not None
    assert [call[0] for call in pipeline.mouse.calls] == ["move_to"]


def test_paused_system_tracks_the_hand_but_sends_no_mouse_commands():
    pipeline = Pipeline(hands=[open_hand()])
    pipeline.controller.start()
    pipeline.controller.pause()

    result = pipeline.processor.process(object())

    assert result.hand is not None
    assert pipeline.mouse.calls == []


def test_missing_hand_leaves_the_cursor_where_it_is():
    pipeline = Pipeline(hands=[None])
    pipeline.controller.start()

    result = pipeline.processor.process(object())

    assert result.hand is None
    assert pipeline.mouse.calls == []


def test_holding_a_fist_pauses_and_does_not_instantly_resume():
    pipeline = Pipeline(hands=[fist()] * 4)
    pipeline.controller.start()

    for _ in range(2):
        pipeline.processor.process(object())
        pipeline.clock.advance(1.0)
    assert pipeline.controller.state is SystemState.PAUSED

    for _ in range(2):  # the fist is still closed: must not instantly toggle back
        pipeline.processor.process(object())
        pipeline.clock.advance(1.0)
    assert pipeline.controller.state is SystemState.PAUSED


# --- GestureRuntime ----------------------------------------------------------------------------


def test_camera_loss_ends_in_safe_off_state_and_reports_the_error():
    pipeline = Pipeline(source=FakeFrameSource(frame_count=2), hands=[open_hand()] * 2)
    errors = []
    pipeline.runtime.add_error_listener(errors.append)

    pipeline.runtime.start()
    wait_until_off(pipeline.controller)

    assert [type(error) for error in errors] == [CameraError]
    assert pipeline.source.closed


def test_frame_listeners_receive_every_processed_frame():
    pipeline = Pipeline(source=FakeFrameSource(frame_count=3), hands=[open_hand()] * 3)
    results = []
    pipeline.runtime.add_frame_listener(lambda frame, result: results.append(result))

    pipeline.runtime.start()
    wait_until_off(pipeline.controller)

    assert len(results) == 3


def test_start_fails_cleanly_when_camera_cannot_be_opened():
    pipeline = Pipeline(source=FakeFrameSource(fail_on_open=True))

    with pytest.raises(CameraError):
        pipeline.runtime.start()

    assert pipeline.controller.state is SystemState.OFF


def test_stop_ends_the_loop_and_releases_the_camera():
    pipeline = Pipeline(source=FakeFrameSource(frame_count=10**9))
    pipeline.runtime.start()
    assert pipeline.controller.state is SystemState.ACTIVE

    pipeline.runtime.stop()

    assert pipeline.controller.state is SystemState.OFF
    assert pipeline.source.closed


def test_toggle_running_starts_then_stops():
    pipeline = Pipeline(source=FakeFrameSource(frame_count=10**9))

    pipeline.runtime.toggle_running()
    assert pipeline.controller.state is SystemState.ACTIVE
    pipeline.runtime.toggle_running()

    assert pipeline.controller.state is SystemState.OFF


def test_runtime_can_be_restarted_after_stopping():
    pipeline = Pipeline(source=FakeFrameSource(frame_count=10**9))

    pipeline.runtime.start()
    pipeline.runtime.stop()
    pipeline.runtime.start()

    assert pipeline.controller.state is SystemState.ACTIVE
    pipeline.runtime.stop()


class StallingFrameSource(FakeFrameSource):
    """read() blocks until released, like a camera driver that hangs."""

    def __init__(self) -> None:
        super().__init__(frame_count=10**9)
        self.release_read = threading.Event()

    def read(self):
        self.release_read.wait(WAIT_S)
        return super().read()


def test_stop_turns_the_system_off_even_while_a_camera_read_hangs():
    source = StallingFrameSource()
    pipeline = Pipeline(source=source)
    pipeline.runtime.start()

    pipeline.runtime.stop()

    assert pipeline.controller.state is SystemState.OFF
    source.release_read.set()


def test_start_waits_for_a_closing_session_before_reopening_the_camera():
    source = StallingFrameSource()
    pipeline = Pipeline(source=source)
    pipeline.runtime.start()
    pipeline.runtime.stop()  # the loop is still stuck in read()
    threading.Timer(0.2, source.release_read.set).start()

    pipeline.runtime.start()

    assert pipeline.controller.state is SystemState.ACTIVE
    pipeline.runtime.stop()


def test_listeners_can_unsubscribe():
    controller = SystemController()
    seen = []
    unsubscribe = controller.subscribe(seen.append)

    controller.start()
    unsubscribe()
    controller.stop()

    assert len(seen) == 1


def _processed_handedness(mirror: bool):
    from dataclasses import replace

    from jestkontrol.domain.landmarks import Handedness

    pipeline = Pipeline(hands=[replace(open_hand(), handedness=Handedness.RIGHT)])
    pipeline.processor._settings = FakeSettingsProvider(Settings(mirror=mirror))
    pipeline.controller.start()
    return pipeline.processor.process(object()).hand.handedness


def test_handedness_is_kept_for_a_mirrored_image():
    from jestkontrol.domain.landmarks import Handedness

    assert _processed_handedness(mirror=True) is Handedness.RIGHT


def test_handedness_is_swapped_when_the_image_is_not_mirrored():
    from jestkontrol.domain.landmarks import Handedness

    assert _processed_handedness(mirror=False) is Handedness.LEFT
