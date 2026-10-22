"""System volume follows the distance between thumb and index fingertips."""

from jestkontrol.application.recognizers.base import GestureContext, GestureRecognizer
from jestkontrol.application.smoothing import ExponentialSmoother
from jestkontrol.domain.geometry import clamp, normalized_distance
from jestkontrol.domain.gestures import GestureEvent, GestureType, VolumeSet
from jestkontrol.domain.landmarks import LandmarkId
from jestkontrol.domain.modes import OperatingMode

# Thumb-index gap (in palm sizes) mapped to 0% and 100% volume.
SILENT_GAP = 0.15
FULL_GAP = 1.15
# Minimum level change worth sending to the audio device.
MIN_LEVEL_CHANGE = 0.01
_MIDDLE_LEVEL = 0.5


class VolumeRecognizer(GestureRecognizer):
    gesture = GestureType.VOLUME
    modes = frozenset({OperatingMode.VOLUME})

    def __init__(self) -> None:
        self._smoother = ExponentialSmoother()
        self._last_sent: float | None = None

    def recognize(self, context: GestureContext) -> list[GestureEvent]:
        settings = context.settings
        gap = normalized_distance(context.hand, LandmarkId.THUMB_TIP, LandmarkId.INDEX_TIP)
        raw_level = clamp((gap - SILENT_GAP) / (FULL_GAP - SILENT_GAP))
        scaled = clamp(_MIDDLE_LEVEL + (raw_level - _MIDDLE_LEVEL) * settings.volume_sensitivity)
        level = self._smoother.smooth(scaled, settings.smoothing_alpha)
        if self._last_sent is not None and abs(level - self._last_sent) < MIN_LEVEL_CHANGE:
            return []
        self._last_sent = level
        return [VolumeSet(level)]
