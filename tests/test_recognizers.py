import pytest

from jestkontrol.application.recognizers.base import GestureContext
from jestkontrol.application.recognizers.left_click_drag import (
    DRAG_HOLD_S,
    LeftClickDragRecognizer,
)
from jestkontrol.application.recognizers.pause_fist import PAUSE_HOLD_S, PauseFistRecognizer
from jestkontrol.application.recognizers.right_click import RightClickRecognizer
from jestkontrol.application.recognizers.scroll import ScrollRecognizer
from jestkontrol.application.recognizers.volume import VolumeRecognizer
from jestkontrol.domain.gestures import (
    Clicked,
    DragEnded,
    DragStarted,
    GestureType,
    MouseButton,
    PauseToggled,
    Scrolled,
    VolumeSet,
)
from jestkontrol.domain.landmarks import LandmarkId
from jestkontrol.domain.settings import Settings
from tests.hands import fist, open_hand, pinch, shifted

SETTINGS = Settings(smoothing_percent=0)


def context(hand, now, settings=SETTINGS):
    return GestureContext(hand, now, settings)


# --- left click / drag -------------------------------------------------------------------------


def test_short_pinch_is_a_left_click_on_release():
    recognizer = LeftClickDragRecognizer()
    pinched = pinch(open_hand(), LandmarkId.INDEX_TIP)

    assert recognizer.recognize(context(pinched, 0.0)) == []
    assert recognizer.recognize(context(pinched, 0.1)) == []
    assert recognizer.recognize(context(open_hand(), 0.15)) == [Clicked(MouseButton.LEFT)]


def test_open_hand_does_not_click():
    assert LeftClickDragRecognizer().recognize(context(open_hand(), 0.0)) == []


def test_long_pinch_starts_a_drag_and_release_drops_without_click():
    recognizer = LeftClickDragRecognizer()
    pinched = pinch(open_hand(), LandmarkId.INDEX_TIP)

    recognizer.recognize(context(pinched, 0.0))
    assert recognizer.recognize(context(pinched, DRAG_HOLD_S)) == [DragStarted()]
    assert recognizer.recognize(context(pinched, DRAG_HOLD_S + 0.5)) == []
    assert recognizer.recognize(context(open_hand(), DRAG_HOLD_S + 0.6)) == [DragEnded()]


def test_drag_is_not_started_when_drag_gesture_is_disabled():
    settings = Settings(enabled_gestures=frozenset({GestureType.LEFT_CLICK}))
    recognizer = LeftClickDragRecognizer()
    pinched = pinch(open_hand(), LandmarkId.INDEX_TIP)

    recognizer.recognize(context(pinched, 0.0, settings))

    assert recognizer.recognize(context(pinched, 1.0, settings)) == []


def test_second_click_within_cooldown_is_ignored():
    recognizer = LeftClickDragRecognizer()
    pinched = pinch(open_hand(), LandmarkId.INDEX_TIP)
    opened = open_hand()

    def tap(start):
        recognizer.recognize(context(pinched, start))
        return recognizer.recognize(context(opened, start + 0.05))

    assert tap(0.0) == [Clicked(MouseButton.LEFT)]
    assert tap(0.1) == []  # inside the 300 ms cooldown
    assert tap(0.6) == [Clicked(MouseButton.LEFT)]


def test_pinch_with_middle_finger_is_not_a_left_click():
    recognizer = LeftClickDragRecognizer()
    middle_pinch = pinch(open_hand(), LandmarkId.MIDDLE_TIP)

    recognizer.recognize(context(middle_pinch, 0.0))

    assert recognizer.recognize(context(open_hand(), 0.1)) == []


def test_reset_during_drag_releases_it():
    recognizer = LeftClickDragRecognizer()
    pinched = pinch(open_hand(), LandmarkId.INDEX_TIP)
    recognizer.recognize(context(pinched, 0.0))
    recognizer.recognize(context(pinched, DRAG_HOLD_S))

    assert recognizer.reset() == [DragEnded()]
    assert recognizer.reset() == []


def test_pinch_hysteresis_ignores_jitter_around_threshold():
    recognizer = LeftClickDragRecognizer()
    pinched = pinch(open_hand(), LandmarkId.INDEX_TIP, gap_in_palms=0.28)
    jitter = pinch(open_hand(), LandmarkId.INDEX_TIP, gap_in_palms=0.33)  # above threshold, below release limit

    recognizer.recognize(context(pinched, 0.0))
    recognizer.recognize(context(jitter, 0.05))

    assert recognizer.recognize(context(pinched, 0.1)) == []  # still the same pinch, no click yet


# --- right click -------------------------------------------------------------------------------


def test_thumb_middle_touch_is_a_right_click_once():
    recognizer = RightClickRecognizer()
    touching = pinch(open_hand(), LandmarkId.MIDDLE_TIP)

    assert recognizer.recognize(context(touching, 0.0)) == [Clicked(MouseButton.RIGHT)]
    assert recognizer.recognize(context(touching, 0.05)) == []


def test_right_click_requires_index_finger_up():
    recognizer = RightClickRecognizer()
    touching = pinch(open_hand(index=False), LandmarkId.MIDDLE_TIP)

    assert recognizer.recognize(context(touching, 0.0)) == []


def test_thumb_index_pinch_is_not_a_right_click():
    recognizer = RightClickRecognizer()

    assert recognizer.recognize(context(pinch(open_hand(), LandmarkId.INDEX_TIP), 0.0)) == []


# --- scroll ------------------------------------------------------------------------------------


def two_fingers():
    return open_hand(ring=False, pinky=False)


def test_scroll_moving_hand_up_scrolls_up():
    recognizer = ScrollRecognizer()

    assert recognizer.recognize(context(two_fingers(), 0.0)) == []
    [event] = recognizer.recognize(context(shifted(two_fingers(), dy=-0.125), 0.1))

    assert event == Scrolled(notches=6)  # 0.625 palm * speed 5 * 2 notches


def test_scroll_moving_hand_down_scrolls_down():
    recognizer = ScrollRecognizer()
    recognizer.recognize(context(two_fingers(), 0.0))

    [event] = recognizer.recognize(context(shifted(two_fingers(), dy=0.1), 0.1))

    assert event.notches < 0


def test_scroll_accumulates_sub_notch_movement():
    recognizer = ScrollRecognizer()
    recognizer.recognize(context(two_fingers(), 0.0))

    first = recognizer.recognize(context(shifted(two_fingers(), dy=-0.01), 0.1))  # 0.5 notch
    second = recognizer.recognize(context(shifted(two_fingers(), dy=-0.02), 0.2))  # +0.5 notch

    assert first == []
    assert second == [Scrolled(notches=1)]


def test_scroll_needs_the_two_finger_pose():
    recognizer = ScrollRecognizer()
    recognizer.recognize(context(open_hand(), 0.0))

    assert recognizer.recognize(context(shifted(open_hand(), dy=-0.1), 0.1)) == []


def test_scroll_does_not_jump_when_pose_is_regained():
    recognizer = ScrollRecognizer()
    recognizer.recognize(context(two_fingers(), 0.0))
    recognizer.recognize(context(open_hand(), 0.1))  # pose lost
    elsewhere = shifted(two_fingers(), dy=-0.3)

    assert recognizer.recognize(context(elsewhere, 0.2)) == []


# --- volume ------------------------------------------------------------------------------------


def test_closed_pinch_is_silent_and_wide_open_is_loud():
    quiet = VolumeRecognizer()
    loud = VolumeRecognizer()

    [silent] = quiet.recognize(context(pinch(open_hand(), LandmarkId.INDEX_TIP), 0.0))
    [full] = loud.recognize(context(open_hand(), 0.0))

    assert silent == VolumeSet(0.0)
    assert full.level == pytest.approx(0.95, abs=0.01)


def test_volume_ignores_changes_smaller_than_one_percent():
    recognizer = VolumeRecognizer()
    recognizer.recognize(context(open_hand(), 0.0))

    assert recognizer.recognize(context(open_hand(), 0.1)) == []


def test_volume_sensitivity_widens_the_range():
    settings = Settings(smoothing_percent=0, volume_sensitivity=2.0)

    [event] = VolumeRecognizer().recognize(context(open_hand(), 0.0, settings))

    assert event.level == pytest.approx(1.0)


# --- pause -------------------------------------------------------------------------------------


def test_fist_held_for_one_second_toggles_pause_once():
    recognizer = PauseFistRecognizer()

    assert recognizer.recognize(context(fist(), 0.0)) == []
    assert recognizer.recognize(context(fist(), PAUSE_HOLD_S - 0.01)) == []
    assert recognizer.recognize(context(fist(), PAUSE_HOLD_S)) == [PauseToggled()]
    assert recognizer.recognize(context(fist(), PAUSE_HOLD_S + 2)) == []


def test_opening_the_fist_rearms_the_pause_gesture():
    recognizer = PauseFistRecognizer()
    recognizer.recognize(context(fist(), 0.0))
    recognizer.recognize(context(fist(), PAUSE_HOLD_S))
    recognizer.recognize(context(open_hand(), 1.5))

    recognizer.recognize(context(fist(), 2.0))

    assert recognizer.recognize(context(fist(), 2.0 + PAUSE_HOLD_S)) == [PauseToggled()]


def test_short_fist_does_not_pause():
    recognizer = PauseFistRecognizer()
    recognizer.recognize(context(fist(), 0.0))
    recognizer.recognize(context(open_hand(), 0.5))

    assert recognizer.recognize(context(fist(), 0.6)) == []
    assert recognizer.recognize(context(fist(), 0.6 + PAUSE_HOLD_S - 0.1)) == []
