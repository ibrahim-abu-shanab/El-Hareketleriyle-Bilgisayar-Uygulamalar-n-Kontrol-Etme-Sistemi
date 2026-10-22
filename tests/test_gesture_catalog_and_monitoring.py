from datetime import datetime

import pytest

from jestkontrol.application.event_log import EventLog, EventRecorder
from jestkontrol.application.frame_processor import FrameResult
from jestkontrol.application.gesture_catalog import (
    GESTURE_CATALOG,
    GestureGroup,
    gesture_info,
    gesture_of,
    gestures_in_group,
    gestures_in_mode,
)
from jestkontrol.application.i18n.catalog_tr import TURKISH
from jestkontrol.application.live_monitor import GESTURE_HOLD_S, LiveMonitor
from jestkontrol.application.recognizers.registry import create_default_recognizers
from jestkontrol.application.system_controller import SystemController
from jestkontrol.domain.gestures import (
    Clicked,
    CursorMoved,
    DragStarted,
    GestureType,
    MouseButton,
    Scrolled,
)
from jestkontrol.domain.landmarks import Point
from jestkontrol.domain.modes import OperatingMode
from tests.fakes import FakeClock
from tests.hands import open_hand

# --- gesture catalog ---------------------------------------------------------------------------


def test_every_gesture_type_is_in_the_catalog_once():
    assert sorted(info.gesture.value for info in GESTURE_CATALOG) == sorted(
        gesture.value for gesture in GestureType
    )


def test_catalog_groups_match_the_modes_the_recognizers_work_in():
    for recognizer in create_default_recognizers():
        group = gesture_info(recognizer.gesture).group
        if group is GestureGroup.GENERAL:
            assert recognizer.modes == frozenset(OperatingMode)
        else:
            assert recognizer.modes == frozenset({OperatingMode(group.value)})


def test_every_catalog_text_key_exists_in_the_translations():
    keys = [
        key
        for info in GESTURE_CATALOG
        for key in (info.name_key, info.short_key, info.description_key, info.fingers_key, info.group_key)
    ]

    assert [key for key in keys if key not in TURKISH] == []


def test_mouse_mode_lists_the_four_mouse_gestures():
    assert [i.gesture for i in gestures_in_mode(OperatingMode.MOUSE)] == [
        GestureType.MOVE,
        GestureType.LEFT_CLICK,
        GestureType.RIGHT_CLICK,
        GestureType.DRAG,
    ]


def test_group_filter_and_unfiltered_listing():
    assert len(gestures_in_group(None)) == len(GESTURE_CATALOG)
    assert [i.gesture for i in gestures_in_group(GestureGroup.GENERAL)] == [GestureType.PAUSE]


def test_only_cursor_movement_is_always_on():
    assert [i.gesture for i in GESTURE_CATALOG if i.always_on] == [GestureType.MOVE]


def test_events_map_to_their_gesture():
    assert gesture_of(Clicked(MouseButton.LEFT)) is GestureType.LEFT_CLICK
    assert gesture_of(Clicked(MouseButton.RIGHT)) is GestureType.RIGHT_CLICK
    assert gesture_of(Scrolled(1)) is GestureType.SCROLL
    assert gesture_of(CursorMoved(Point(0, 0))) is GestureType.MOVE


# --- event log ---------------------------------------------------------------------------------


def make_log():
    moments = iter(datetime(2026, 10, 14, 14, 0, second) for second in range(100))
    return EventLog(now=lambda: next(moments))


def test_log_returns_newest_first_and_is_bounded():
    log = make_log()
    for index in range(60):
        log.add(f"event.{index}")

    recent = log.recent(3)

    assert [event.key for event in recent] == ["event.59", "event.58", "event.57"]
    assert len(log.recent(100)) == 50


def test_recorder_logs_clicks_and_drags_but_not_cursor_movement():
    log = make_log()
    recorder = EventRecorder(log)
    events = (Clicked(MouseButton.LEFT), CursorMoved(Point(0, 0)), DragStarted(), Clicked(MouseButton.RIGHT))

    recorder.on_frame(object(), FrameResult(None, events))

    assert [e.key for e in log.recent(10)][::-1] == [
        "event.left_click",
        "event.drag",
        "event.right_click",
    ]


def test_recorder_logs_lifecycle_and_mode_changes():
    log = make_log()
    recorder = EventRecorder(log)
    controller = SystemController()
    controller.subscribe(recorder.on_status)

    controller.start()
    controller.set_mode(OperatingMode.VOLUME)
    controller.pause()
    controller.resume()
    controller.stop()

    assert [e.key for e in log.recent(10)][::-1] == [
        "event.started",
        "event.mode",
        "event.paused",
        "event.resumed",
        "event.stopped",
    ]
    mode_event = next(e for e in log.recent(10) if e.key == "event.mode")
    assert mode_event.params == {"mode": "mode.volume"}


# --- live monitor ------------------------------------------------------------------------------


def test_monitor_starts_empty():
    assert LiveMonitor(FakeClock()).snapshot().frame is None


def test_monitor_exposes_the_latest_frame_hand_and_moving_gesture():
    monitor = LiveMonitor(FakeClock())
    hand = open_hand()
    frame = object()

    monitor.on_frame(frame, FrameResult(hand, (CursorMoved(Point(0.5, 0.5)),)))

    snapshot = monitor.snapshot()
    assert (snapshot.frame, snapshot.hand, snapshot.gesture) == (frame, hand, GestureType.MOVE)


def test_click_stays_on_display_briefly_then_falls_back_to_movement():
    clock = FakeClock()
    monitor = LiveMonitor(clock)
    moving = (CursorMoved(Point(0.5, 0.5)),)

    monitor.on_frame(object(), FrameResult(open_hand(), (Clicked(MouseButton.LEFT), *moving)))
    clock.advance(GESTURE_HOLD_S / 2)
    monitor.on_frame(object(), FrameResult(open_hand(), moving))
    assert monitor.snapshot().gesture is GestureType.LEFT_CLICK

    clock.advance(GESTURE_HOLD_S)
    monitor.on_frame(object(), FrameResult(open_hand(), moving))
    assert monitor.snapshot().gesture is GestureType.MOVE


def test_no_events_means_no_gesture_and_clear_resets():
    monitor = LiveMonitor(FakeClock())
    monitor.on_frame(object(), FrameResult(None, ()))
    assert monitor.snapshot().gesture is None

    monitor.on_frame(object(), FrameResult(None, (Clicked(MouseButton.LEFT),)))
    monitor.clear()

    assert monitor.snapshot().frame is None
