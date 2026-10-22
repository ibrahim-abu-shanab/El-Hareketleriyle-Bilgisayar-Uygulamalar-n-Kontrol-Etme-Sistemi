"""Cursor movement: the index fingertip drives the pointer."""

from jestkontrol.application.cursor_mapper import map_to_screen
from jestkontrol.application.recognizers.base import GestureContext, GestureRecognizer
from jestkontrol.application.smoothing import ExponentialSmoother
from jestkontrol.domain.gestures import CursorMoved, GestureEvent, GestureType
from jestkontrol.domain.landmarks import LandmarkId, Point
from jestkontrol.domain.modes import OperatingMode


class MoveRecognizer(GestureRecognizer):
    gesture = GestureType.MOVE
    modes = frozenset({OperatingMode.MOUSE})

    def __init__(self) -> None:
        self._x = ExponentialSmoother()
        self._y = ExponentialSmoother()

    def recognize(self, context: GestureContext) -> list[GestureEvent]:
        settings = context.settings
        target = map_to_screen(context.hand[LandmarkId.INDEX_TIP], settings)
        alpha = settings.smoothing_alpha
        position = Point(
            self._x.smooth(target.x, alpha),
            self._y.smooth(target.y, alpha),
        )
        return [CursorMoved(position)]
