"""Maps a fingertip position in the camera frame to a normalized screen position."""

from jestkontrol.domain.geometry import clamp
from jestkontrol.domain.landmarks import Point
from jestkontrol.domain.settings import Settings

_CENTER = 0.5


def map_to_screen(fingertip: Point, settings: Settings) -> Point:
    return Point(
        _map_axis(fingertip.x, settings),
        _map_axis(fingertip.y, settings),
    )


def _map_axis(value: float, settings: Settings) -> float:
    margin = settings.active_area_margin
    stretched = (value - margin) / (1 - 2 * margin)  # active area -> [0, 1]
    amplified = _CENTER + (stretched - _CENTER) * settings.sensitivity
    return clamp(amplified)
