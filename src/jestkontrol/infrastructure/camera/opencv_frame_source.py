"""Webcam capture through OpenCV (F1: camera selection, mirroring, resolution)."""

import cv2

from jestkontrol.application.ports import CameraError, Frame, SettingsProvider


class OpenCvFrameSource:
    def __init__(self, settings: SettingsProvider) -> None:
        self._settings = settings
        self._capture: cv2.VideoCapture | None = None

    def open(self) -> None:
        settings = self._settings.current
        capture = cv2.VideoCapture(settings.camera_index, cv2.CAP_DSHOW)
        if not capture.isOpened():
            capture.release()
            raise CameraError(f"Camera {settings.camera_index} could not be opened")
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
