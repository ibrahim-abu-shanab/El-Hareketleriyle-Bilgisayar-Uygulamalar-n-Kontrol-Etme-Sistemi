"""System master volume through Windows Core Audio (pycaw)."""

import comtypes
from pycaw.pycaw import AudioUtilities

from jestkontrol.domain.geometry import clamp


class PycawVolume:
    def __init__(self) -> None:
        self._endpoint = None

    def set_level(self, level: float) -> None:
        self._endpoint_volume().SetMasterVolumeLevelScalar(clamp(level), None)

    def _endpoint_volume(self):
        # COM objects belong to the thread that created them, so create lazily on the loop thread.
        if self._endpoint is None:
            comtypes.CoInitialize()
            self._endpoint = AudioUtilities.GetSpeakers().EndpointVolume
        return self._endpoint
