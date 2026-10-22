"""Cameras the user can choose from, and how one is picked when the user has not chosen."""

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CameraDevice:
    index: int  # position in the system's camera list, as the capture backend counts it
    name: str


# Software cameras (phone apps, streaming tools) and infrared sensors are valid choices, but a poor
# default: they often deliver black or grayscale pictures. A bare "OBS" is a tool; "OBSBOT" is a webcam.
_NOT_A_DEFAULT = re.compile(
    r"virtual|nvidia broadcast|snap camera"
    r"|\b(?:iriun|obs|droidcam|epoccam|ivcam|manycam|camo|xsplit|splitcam|vcam|ir|infrared)\b",
    re.IGNORECASE,
)


def is_default_candidate(name: str) -> bool:
    """True for a physical color camera, the kind that makes a good automatic choice."""
    return _NOT_A_DEFAULT.search(name) is None


def choose_camera(cameras: Sequence[CameraDevice], saved_name: str) -> CameraDevice | None:
    """The camera the user saved; with no saved choice, the first physical camera (else the first one).

    A saved camera that is no longer present gives None instead of silently switching to another one.
    """
    if saved_name:
        return next((camera for camera in cameras if camera.name == saved_name), None)
    preferred = next((camera for camera in cameras if is_default_candidate(camera.name)), None)
    return preferred or next(iter(cameras), None)


def unique_names(cameras: Sequence[CameraDevice]) -> list[CameraDevice]:
    """Gives identical names a suffix ("USB Camera", "USB Camera (2)") so a name identifies one camera."""
    seen: Counter[str] = Counter()
    result = []
    for camera in cameras:
        seen[camera.name] += 1
        suffix = f" ({seen[camera.name]})" if seen[camera.name] > 1 else ""
        result.append(CameraDevice(camera.index, camera.name + suffix))
    return result
