"""Finds which camera indices can be opened."""

import cv2

MAX_PROBED_CAMERAS = 4


class OpenCvCameraCatalog:
    def available_indices(self, keep: int | None = None) -> list[int]:
        """Camera indices that open now; ``keep`` (e.g. the camera in use) is always listed."""
        found = [index for index in range(MAX_PROBED_CAMERAS) if index == keep or _opens(index)]
        return found or [0]


def _opens(index: int) -> bool:
    capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    try:
        return capture.isOpened()
    finally:
        capture.release()
