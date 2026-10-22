"""Webcam capture through OpenCV (F1: camera selection, mirroring, resolution)."""

import cv2

from jestkontrol.application.camera_selection import CameraSelection
from jestkontrol.application.ports import CameraError, Frame, SettingsProvider


class OpenCvFrameSource:
    def __init__(self, settings: SettingsProvider, selection: CameraSelection) -> None:
        self._settings = settings
        self._selection = selection
        self._capture: cv2.VideoCapture | None = None

    def open(self) -> None:
        self._selection.refresh()  # numbers shift when devices appear or go: never open a stale one
        device = self._selection.selected()
        if device is None:
            saved = self._selection.label()
            raise CameraError(f"Camera {saved!r} is not connected" if saved else "No camera found")
        settings = self._settings.current
        capture = cv2.VideoCapture(device.index, cv2.CAP_DSHOW)
        if not capture.isOpened():
            capture.release()
            raise CameraError(f"Camera {device.name!r} could not be opened")
        width, height = settings.resolution
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self._capture = capture

    def read(self) -> Frame:
        if self._capture is None:
            raise CameraError("Camera is not open")
        delivered, frame = self._capture.read()
        if not delivered:
            raise CameraError("Camera stopped delivering frames")
        return cv2.flip(frame, 1) if self._settings.current.mirror else frame

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
