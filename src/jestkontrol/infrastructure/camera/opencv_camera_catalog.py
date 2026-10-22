"""Lists the cameras by name, numbered exactly as OpenCV's DirectShow backend numbers them."""

import logging

import cv2
from cv2_enumerate_cameras import enumerate_cameras

from jestkontrol.domain.camera import CameraDevice

logger = logging.getLogger(__name__)


class OpenCvCameraCatalog:
    def list_cameras(self) -> list[CameraDevice]:
        """Reads names from the system without opening any camera, so it is quick and has no side effects."""
        try:
            infos = enumerate_cameras(cv2.CAP_DSHOW)
        except Exception:  # an enumeration problem must not stop the app: the list is just empty
            logger.exception("Could not list the cameras")
            return []
        return [CameraDevice(info.index, info.name or f"Camera {info.index + 1}") for info in infos]
