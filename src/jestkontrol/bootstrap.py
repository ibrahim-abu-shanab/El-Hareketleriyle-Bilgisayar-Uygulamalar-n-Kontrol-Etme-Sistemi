"""Composition root: the only place where application ports are bound to infrastructure adapters."""

import os
from pathlib import Path

from jestkontrol.application.services import Adapters, AppServices, create_services
from jestkontrol.infrastructure.camera.opencv_camera_catalog import OpenCvCameraCatalog
from jestkontrol.infrastructure.camera.opencv_frame_source import OpenCvFrameSource
from jestkontrol.infrastructure.hotkey.win_hotkey_listener import WinHotkeyListener
from jestkontrol.infrastructure.os_control.pyautogui_mouse import PyAutoGuiMouse, PyAutoGuiScreen
from jestkontrol.infrastructure.os_control.pycaw_volume import PycawVolume
from jestkontrol.infrastructure.storage.csv_results_exporter import CsvResultsExporter
from jestkontrol.infrastructure.storage.json_diagnostics_repository import (
    JsonDiagnosticsRepository,
)
from jestkontrol.infrastructure.storage.json_settings_repository import JsonSettingsRepository
from jestkontrol.infrastructure.system_clock import SystemClock
from jestkontrol.infrastructure.tracking.mediapipe_hand_tracker import MediaPipeHandTracker

APP_FOLDER_NAME = "JestKontrol"
SETTINGS_FILE_NAME = "settings.json"
HISTORY_FILE_NAME = "test_history.json"


def default_data_folder() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home()))
    return base / APP_FOLDER_NAME


def create_application(data_folder: Path | None = None) -> AppServices:
    folder = data_folder or default_data_folder()
    adapters = Adapters(
        clock=SystemClock(),
        tracker=MediaPipeHandTracker(),
        mouse=PyAutoGuiMouse(),
        screen=PyAutoGuiScreen(),
        volume=PycawVolume(),
        hotkey=WinHotkeyListener(),
        cameras=OpenCvCameraCatalog(),
        settings_repository=JsonSettingsRepository(folder / SETTINGS_FILE_NAME),
        diagnostics_repository=JsonDiagnosticsRepository(folder / HISTORY_FILE_NAME),
        exporter=CsvResultsExporter(),
    )
    return create_services(adapters, OpenCvFrameSource)
