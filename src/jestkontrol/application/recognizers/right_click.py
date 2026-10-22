"""Right click: briefly touching thumb and middle fingertips while the index finger stays up."""

from jestkontrol.application.recognizers.base import GestureContext, GestureRecognizer
from jestkontrol.application.recognizers.cooldown import Cooldown
from jestkontrol.application.recognizers.pinch import PinchDetector
from jestkontrol.domain.geometry import is_finger_extended
from jestkontrol.domain.gestures import Clicked, GestureEvent, GestureType, MouseButton
from jestkontrol.domain.landmarks import LandmarkId
from jestkontrol.domain.modes import OperatingMode


class RightClickRecognizer(GestureRecognizer):
    gesture = GestureType.RIGHT_CLICK
    modes = frozenset({OperatingMode.MOUSE})

    def __init__(self) -> None:
        self._pinch = PinchDetector(LandmarkId.MIDDLE_TIP, rival_tip=LandmarkId.INDEX_TIP)
        self._cooldown = Cooldown()
        self._was_pinched = False

    def recognize(self, context: GestureContext) -> list[GestureEvent]:
        settings = context.settings
        pinched = self._pinch.update(context.hand, settings.click_threshold)
        touched_now = pinched and not self._was_pinched
        self._was_pinched = pinched
        if (
            touched_now
            and is_finger_extended(context.hand, "index")
            and self._cooldown.try_fire(context.now, settings.click_cooldown_s)
        ):
            return [Clicked(MouseButton.RIGHT)]
        return []

    def reset(self) -> list[GestureEvent]:
        self._pinch.reset()
        self._was_pinched = False
        return []
