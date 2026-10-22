"""Which camera the system uses: the cameras the system knows plus the user's saved choice."""

import threading

from jestkontrol.application.ports import CameraCatalog
from jestkontrol.application.settings_store import SettingsStore
from jestkontrol.domain.camera import CameraDevice, choose_camera, unique_names


class CameraSelection:
    def __init__(self, catalog: CameraCatalog, settings: SettingsStore) -> None:
        self._catalog = catalog
        self._settings = settings
        self._lock = threading.Lock()
        self._devices: list[CameraDevice] | None = None

    def devices(self) -> list[CameraDevice]:
        """The cameras found by the last enumeration (enumerates on first use)."""
        with self._lock:
            if self._devices is None:
                self._devices = unique_names(self._catalog.list_cameras())
            return list(self._devices)

    def refresh(self) -> list[CameraDevice]:
        """Looks for cameras again (a phone app may have started, a USB camera been plugged in)."""
        with self._lock:
            self._devices = unique_names(self._catalog.list_cameras())
            return list(self._devices)

    def selected(self) -> CameraDevice | None:
        """The camera to use now; None when there is none, or when the saved one is not connected."""
        return choose_camera(self.devices(), self._settings.current.camera_name)

    def label(self) -> str:
        """Name to show for the camera: the one in use, else the saved one that is missing."""
        selected = self.selected()
        return selected.name if selected else self._settings.current.camera_name

    def select(self, device: CameraDevice) -> None:
        """Saves the choice by name: numbers change when devices come and go."""
        self._settings.change(camera_name=device.name)
