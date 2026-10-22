import pytest

from jestkontrol.application.cursor_mapper import map_to_screen
from jestkontrol.application.recognizers.base import GestureContext
from jestkontrol.application.recognizers.move import MoveRecognizer
from jestkontrol.application.smoothing import ExponentialSmoother
from jestkontrol.domain.gestures import CursorMoved
from jestkontrol.domain.landmarks import LandmarkId, Point
from jestkontrol.domain.settings import Settings
from tests.hands import open_hand, with_landmark


def test_smoother_passes_first_sample_through():
    assert ExponentialSmoother().smooth(0.8, alpha=0.4) == 0.8


def test_smoother_moves_a_fraction_towards_target():
    smoother = ExponentialSmoother()
    smoother.smooth(0.0, alpha=0.5)

    assert smoother.smooth(1.0, alpha=0.5) == pytest.approx(0.5)


def test_smoother_alpha_one_means_no_smoothing():
    smoother = ExponentialSmoother()
    smoother.smooth(0.0, alpha=1)

    assert smoother.smooth(0.7, alpha=1) == pytest.approx(0.7)


def test_active_area_edges_map_to_screen_edges():
    settings = Settings(sensitivity=1.0, active_area_margin_percent=15)

    top_left = map_to_screen(Point(0.15, 0.15), settings)
    bottom_right = map_to_screen(Point(0.85, 0.85), settings)

    assert (top_left.x, top_left.y) == pytest.approx((0.0, 0.0))
    assert (bottom_right.x, bottom_right.y) == pytest.approx((1.0, 1.0))


def test_positions_outside_active_area_are_clamped():
    mapped = map_to_screen(Point(0.0, 1.0), Settings(sensitivity=1.0))

    assert (mapped.x, mapped.y) == (0.0, 1.0)


def test_sensitivity_amplifies_movement_around_center():
    point = Point(0.6, 0.5)

    normal = map_to_screen(point, Settings(sensitivity=1.0))
    amplified = map_to_screen(point, Settings(sensitivity=2.0))

    assert amplified.x - 0.5 == pytest.approx(2 * (normal.x - 0.5))


def test_move_recognizer_follows_index_fingertip_with_smoothing():
    recognizer = MoveRecognizer()
    settings = Settings(smoothing_percent=50, sensitivity=1.0, active_area_margin_percent=0)
    left = with_landmark(open_hand(), LandmarkId.INDEX_TIP, Point(0.0, 0.5))
    right = with_landmark(open_hand(), LandmarkId.INDEX_TIP, Point(1.0, 0.5))

    recognizer.recognize(GestureContext(left, 0.0, settings))
    [event] = recognizer.recognize(GestureContext(right, 0.1, settings))

    assert isinstance(event, CursorMoved)
    assert event.position.x == pytest.approx(0.5)
