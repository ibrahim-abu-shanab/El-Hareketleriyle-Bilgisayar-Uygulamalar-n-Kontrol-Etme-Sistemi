"""Scale-independent geometry on hand landmarks."""

import math

from jestkontrol.domain.landmarks import HandFrame, LandmarkId, Point

# A finger counts as extended when its tip is farther from the wrist than its PIP joint.
_FINGER_JOINTS: dict[str, tuple[LandmarkId, LandmarkId]] = {
    "index": (LandmarkId.INDEX_TIP, LandmarkId.INDEX_PIP),
    "middle": (LandmarkId.MIDDLE_TIP, LandmarkId.MIDDLE_PIP),
    "ring": (LandmarkId.RING_TIP, LandmarkId.RING_PIP),
    "pinky": (LandmarkId.PINKY_TIP, LandmarkId.PINKY_PIP),
}


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return min(max(value, lower), upper)


def distance(a: Point, b: Point) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def palm_size(hand: HandFrame) -> float:
    """Wrist to middle-finger knuckle: the reference length that makes distances hand-size independent."""
    return distance(hand[LandmarkId.WRIST], hand[LandmarkId.MIDDLE_MCP])


def normalized_distance(hand: HandFrame, a: LandmarkId, b: LandmarkId) -> float:
    """Distance between two landmarks expressed in palm sizes."""
    palm = palm_size(hand)
    if palm == 0:
        return math.inf
    return distance(hand[a], hand[b]) / palm


def is_finger_extended(hand: HandFrame, finger: str) -> bool:
    tip, pip = _FINGER_JOINTS[finger]
    wrist = hand[LandmarkId.WRIST]
    return distance(wrist, hand[tip]) > distance(wrist, hand[pip])


def is_fist(hand: HandFrame) -> bool:
    return not any(is_finger_extended(hand, finger) for finger in _FINGER_JOINTS)
