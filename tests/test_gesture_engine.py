from jestkontrol.application.gesture_engine import GestureEngine
from jestkontrol.application.recognizers.left_click_drag import DRAG_HOLD_S
from jestkontrol.application.recognizers.registry import create_default_recognizers
from jestkontrol.domain.gestures import (
    CursorMoved,
    DragEnded,
    DragStarted,
    GestureType,
    PauseToggled,
    Scrolled,
)
from jestkontrol.domain.landmarks import LandmarkId
from jestkontrol.domain.modes import OperatingMode, SystemState
from jestkontrol.domain.settings import Settings
from tests.hands import fist, open_hand, pinch, shifted

SETTINGS = Settings(smoothing_percent=0)
MOUSE, SCROLL = OperatingMode.MOUSE, OperatingMode.SCROLL
ACTIVE, PAUSED, OFF = SystemState.ACTIVE, SystemState.PAUSED, SystemState.OFF


def make_engine() -> GestureEngine:
    return GestureEngine(create_default_recognizers())


def types_of(events) -> list[type]:
    return [type(event) for event in events]


def test_mouse_mode_moves_the_cursor():
    events = make_engine().process(open_hand(), 0.0, SETTINGS, MOUSE, ACTIVE)

    assert CursorMoved in types_of(events)


def test_scroll_mode_does_not_move_the_cursor():
    engine = make_engine()
    two_fingers = open_hand(ring=False, pinky=False)
    engine.process(two_fingers, 0.0, SETTINGS, SCROLL, ACTIVE)

    events = engine.process(shifted(two_fingers, dy=-0.125), 0.1, SETTINGS, SCROLL, ACTIVE)

    assert types_of(events) == [Scrolled]


def test_off_state_produces_nothing():
    assert make_engine().process(open_hand(), 0.0, SETTINGS, MOUSE, OFF) == []


def test_paused_state_only_listens_for_the_resume_fist():
    engine = make_engine()

    assert engine.process(open_hand(), 0.0, SETTINGS, MOUSE, PAUSED) == []
    engine.process(fist(), 1.0, SETTINGS, MOUSE, PAUSED)
    events = engine.process(fist(), 2.0, SETTINGS, MOUSE, PAUSED)

    assert types_of(events) == [PauseToggled]


def test_disabled_gesture_is_not_recognized():
    settings = Settings(smoothing_percent=0, enabled_gestures=frozenset())
    engine = make_engine()
    engine.process(pinch(open_hand(), LandmarkId.INDEX_TIP), 0.0, settings, MOUSE, ACTIVE)
    events = engine.process(open_hand(), 0.1, settings, MOUSE, ACTIVE)

    assert types_of(events) == [CursorMoved]  # no click even though the gesture was performed


def start_drag(engine):
    pinched = pinch(open_hand(), LandmarkId.INDEX_TIP)
    engine.process(pinched, 0.0, SETTINGS, MOUSE, ACTIVE)
    events = engine.process(pinched, DRAG_HOLD_S, SETTINGS, MOUSE, ACTIVE)
    assert DragStarted in types_of(events)


def test_losing_the_hand_releases_a_drag():
    engine = make_engine()
    start_drag(engine)

    assert engine.process(None, 1.0, SETTINGS, MOUSE, ACTIVE) == [DragEnded()]


def test_pausing_during_a_drag_releases_it():
    engine = make_engine()
    start_drag(engine)

    events = engine.process(open_hand(), 1.0, SETTINGS, MOUSE, PAUSED)

    assert DragEnded in types_of(events)


def test_switching_mode_during_a_drag_releases_it():
    engine = make_engine()
    start_drag(engine)

    events = engine.process(open_hand(), 1.0, SETTINGS, SCROLL, ACTIVE)

    assert DragEnded in types_of(events)


def test_release_all_closes_in_progress_gestures_once():
    engine = make_engine()
    start_drag(engine)

    assert engine.release_all() == [DragEnded()]
    assert engine.release_all() == []


def test_move_is_always_part_of_mouse_mode_even_if_drag_disabled():
    settings = Settings(smoothing_percent=0, enabled_gestures=frozenset({GestureType.LEFT_CLICK}))

    events = make_engine().process(open_hand(), 0.0, settings, MOUSE, ACTIVE)

    assert CursorMoved in types_of(events)
