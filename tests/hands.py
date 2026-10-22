"""Builders for synthetic hands (palm size of an open hand is 0.2)."""

from dataclasses import replace

from jestkontrol.domain.landmarks import HandFrame, LandmarkId, Point

OPEN_HAND_PALM = 0.2

_OPEN_HAND: dict[int, tuple[float, float]] = {
    0: (0.50, 0.90),
    1: (0.45, 0.85), 2: (0.40, 0.78), 3: (0.37, 0.72), 4: (0.34, 0.68),
    5: (0.44, 0.72), 6: (0.43, 0.62), 7: (0.43, 0.55), 8: (0.43, 0.48),
    9: (0.50, 0.70), 10: (0.50, 0.59), 11: (0.50, 0.52), 12: (0.50, 0.45),
    13: (0.56, 0.72), 14: (0.57, 0.62), 15: (0.57, 0.56), 16: (0.57, 0.50),
    17: (0.62, 0.75), 18: (0.63, 0.67), 19: (0.63, 0.62), 20: (0.64, 0.58),
}  # fmt: skip

_CURLED_TIPS: dict[int, tuple[float, float]] = {
    8: (0.44, 0.80), 12: (0.50, 0.78), 16: (0.56, 0.80), 20: (0.62, 0.82),
}  # fmt: skip

_FINGER_TIPS: dict[str, int] = {"index": 8, "middle": 12, "ring": 16, "pinky": 20}


def _frame(points: dict[int, tuple[float, float]]) -> HandFrame:
    return HandFrame(tuple(Point(*points[i]) for i in range(21)))


def open_hand(**finger_up: bool) -> HandFrame:
    """Open hand; pass e.g. ``ring=False`` to curl a finger."""
    points = dict(_OPEN_HAND)
    for finger, is_up in finger_up.items():
        if not is_up:
            tip = _FINGER_TIPS[finger]
            points[tip] = _CURLED_TIPS[tip]
    return _frame(points)


def fist() -> HandFrame:
    return open_hand(index=False, middle=False, ring=False, pinky=False)


def with_landmark(hand: HandFrame, landmark: LandmarkId, point: Point) -> HandFrame:
    landmarks = list(hand.landmarks)
    landmarks[landmark] = point
    return replace(hand, landmarks=tuple(landmarks))


def pinch(hand: HandFrame, finger_tip: LandmarkId, gap_in_palms: float = 0.05) -> HandFrame:
    """Place the thumb tip ``gap_in_palms`` palm sizes to the side of another fingertip."""
    target = hand[finger_tip]
    gap = gap_in_palms * OPEN_HAND_PALM
    return with_landmark(hand, LandmarkId.THUMB_TIP, Point(target.x - gap, target.y))


def shifted(hand: HandFrame, dx: float = 0.0, dy: float = 0.0) -> HandFrame:
    return replace(hand, landmarks=tuple(Point(p.x + dx, p.y + dy) for p in hand.landmarks))
