"""Left click and drag-and-drop from a single thumb–index pinch.

A short pinch is a click (fired on release); a pinch held for DRAG_HOLD_S starts a drag
that ends when the pinch opens.
"""

from enum import Enum, auto

from jestkontrol.application.recognizers.base import GestureContext, GestureRecognizer
from jestkontrol.application.recognizers.cooldown import Cooldown
from jestkontrol.application.recognizers.pinch import PinchDetector
from jestkontrol.domain.gestures import (
    Clicked,
    DragEnded,
    DragStarted,
    GestureEvent,
    GestureType,
    MouseButton,
)
from jestkontrol.domain.landmarks import LandmarkId
from jestkontrol.domain.modes import OperatingMode

DRAG_HOLD_S = 0.3


class _Phase(Enum):
    IDLE = auto()
    PINCHING = auto()
    DRAGGING = auto()


class LeftClickDragRecognizer(GestureRecognizer):
    gesture = GestureType.LEFT_CLICK
    modes = frozenset({OperatingMode.MOUSE})

    def __init__(self) -> None:
        self._pinch = PinchDetector(LandmarkId.INDEX_TIP, rival_tip=LandmarkId.MIDDLE_TIP)
        self._cooldown = Cooldown()
        self._phase = _Phase.IDLE
        self._pinch_started_at = 0.0

    def recognize(self, context: GestureContext) -> list[GestureEvent]:
        pinched = self._pinch.update(context.hand, context.settings.click_threshold)
        match self._phase:
            case _Phase.IDLE:
                return self._on_idle(pinched, context)
            case _Phase.PINCHING:
                return self._on_pinching(pinched, context)
            case _Phase.DRAGGING:
                return self._on_dragging(pinched)

    def reset(self) -> list[GestureEvent]:
        events: list[GestureEvent] = [DragEnded()] if self._phase is _Phase.DRAGGING else []
        self._phase = _Phase.IDLE
        self._pinch.reset()
        return events

    def _on_idle(self, pinched: bool, context: GestureContext) -> list[GestureEvent]:
        if pinched:
            self._phase = _Phase.PINCHING
            self._pinch_started_at = context.now
        return []

    def _on_pinching(self, pinched: bool, context: GestureContext) -> list[GestureEvent]:
        if not pinched:
            self._phase = _Phase.IDLE
            return self._click_if_allowed(context)
        if self._should_start_drag(context):
            self._phase = _Phase.DRAGGING
            return [DragStarted()]
        return []

    def _on_dragging(self, pinched: bool) -> list[GestureEvent]:
        if pinched:
            return []
        self._phase = _Phase.IDLE
        return [DragEnded()]

    def _should_start_drag(self, context: GestureContext) -> bool:
        held_for = context.now - self._pinch_started_at
        return held_for >= DRAG_HOLD_S and context.settings.is_enabled(GestureType.DRAG)

    def _click_if_allowed(self, context: GestureContext) -> list[GestureEvent]:
        if self._cooldown.try_fire(context.now, context.settings.click_cooldown_s):
            return [Clicked(MouseButton.LEFT)]
        return []
