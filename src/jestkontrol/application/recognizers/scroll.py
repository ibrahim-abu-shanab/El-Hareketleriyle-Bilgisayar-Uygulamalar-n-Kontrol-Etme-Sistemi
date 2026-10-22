"""Scrolling: with index and middle fingers raised, moving the hand up or down scrolls the page."""

from jestkontrol.application.recognizers.base import GestureContext, GestureRecognizer
from jestkontrol.domain.geometry import is_finger_extended, palm_size
from jestkontrol.domain.gestures import GestureEvent, GestureType, Scrolled
from jestkontrol.domain.landmarks import HandFrame, LandmarkId
from jestkontrol.domain.modes import OperatingMode

NOTCHES_PER_PALM_PER_SPEED = 2.0


class ScrollRecognizer(GestureRecognizer):
    gesture = GestureType.SCROLL
    modes = frozenset({OperatingMode.SCROLL})

    def __init__(self) -> None:
        self._last_y: float | None = None
        self._pending_notches = 0.0

    def recognize(self, context: GestureContext) -> list[GestureEvent]:
        hand = context.hand
        palm = palm_size(hand)
        if not _is_scroll_pose(hand) or palm == 0:
            return self.reset()
        y = _fingers_height(hand)
        previous_y, self._last_y = self._last_y, y
        if previous_y is None:
            return []
        upward_palms = (previous_y - y) / palm
        self._pending_notches += (
            upward_palms * context.settings.scroll_speed * NOTCHES_PER_PALM_PER_SPEED
        )
        notches = int(self._pending_notches)
        self._pending_notches -= notches
        return [Scrolled(notches)] if notches else []

    def reset(self) -> list[GestureEvent]:
        self._last_y = None
        self._pending_notches = 0.0
        return []


def _is_scroll_pose(hand: HandFrame) -> bool:
    return (
        is_finger_extended(hand, "index")
        and is_finger_extended(hand, "middle")
        and not is_finger_extended(hand, "ring")
        and not is_finger_extended(hand, "pinky")
    )


def _fingers_height(hand: HandFrame) -> float:
    return (hand[LandmarkId.INDEX_TIP].y + hand[LandmarkId.MIDDLE_TIP].y) / 2
