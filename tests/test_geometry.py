import pytest

from jestkontrol.domain.geometry import (
    is_finger_extended,
    is_fist,
    normalized_distance,
    palm_size,
)
from jestkontrol.domain.landmarks import HandFrame, LandmarkId, Point
from tests.hands import OPEN_HAND_PALM, fist, open_hand, pinch


def test_palm_size_is_wrist_to_middle_knuckle():
    assert palm_size(open_hand()) == pytest.approx(OPEN_HAND_PALM)


def test_normalized_distance_is_expressed_in_palm_sizes():
    hand = pinch(open_hand(), LandmarkId.INDEX_TIP, gap_in_palms=0.25)

    distance = normalized_distance(hand, LandmarkId.THUMB_TIP, LandmarkId.INDEX_TIP)

    assert distance == pytest.approx(0.25)


def test_normalized_distance_is_infinite_for_degenerate_palm():
    hand = HandFrame(tuple(Point(0.5, 0.5) for _ in range(21)))

    assert normalized_distance(hand, LandmarkId.THUMB_TIP, LandmarkId.INDEX_TIP) == float("inf")


@pytest.mark.parametrize("finger", ["index", "middle", "ring", "pinky"])
def test_open_hand_has_all_fingers_extended(finger):
    assert is_finger_extended(open_hand(), finger)


@pytest.mark.parametrize("finger", ["index", "middle", "ring", "pinky"])
def test_curled_finger_is_not_extended(finger):
    assert not is_finger_extended(open_hand(**{finger: False}), finger)


def test_fist_detection():
    assert is_fist(fist())
    assert not is_fist(open_hand())
    assert not is_fist(open_hand(index=False, ring=False, pinky=False))


def test_hand_requires_21_landmarks():
    with pytest.raises(ValueError):
        HandFrame((Point(0, 0),) * 20)
