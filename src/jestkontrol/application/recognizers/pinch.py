"""Thumb-to-fingertip pinch detection with hysteresis."""

from jestkontrol.domain.geometry import normalized_distance
from jestkontrol.domain.landmarks import HandFrame, LandmarkId

# Once pinched, the fingers must open this much wider than the threshold to count as released,
# so landmark jitter around the threshold does not produce phantom clicks.
RELEASE_HYSTERESIS = 1.25


class PinchDetector:
    """Detects a thumb pinch with ``fingertip``; the thumb must be nearer to it than to ``rival_tip``."""

    def __init__(self, fingertip: LandmarkId, rival_tip: LandmarkId) -> None:
        self._fingertip = fingertip
        self._rival_tip = rival_tip
        self._pinched = False

    def update(self, hand: HandFrame, threshold: float) -> bool:
        """``threshold`` is the pinch distance limit in palm sizes."""
        gap = normalized_distance(hand, LandmarkId.THUMB_TIP, self._fingertip)
        rival_gap = normalized_distance(hand, LandmarkId.THUMB_TIP, self._rival_tip)
        limit = threshold * RELEASE_HYSTERESIS if self._pinched else threshold
        self._pinched = gap < limit and gap <= rival_gap
        return self._pinched

    def reset(self) -> None:
        self._pinched = False
