import cv2
import pytest

from jestkontrol.application.ports import CameraError
from jestkontrol.domain.settings import Settings
from jestkontrol.infrastructure.camera.opencv_frame_source import OpenCvFrameSource
from tests.test_camera_selection import make


class RecordingCapture:
    """Stands in for cv2.VideoCapture and remembers which camera was asked for."""

    opened: list[tuple[int, int]] = []

    def __init__(self, index, backend):
        RecordingCapture.opened.append((index, backend))

    def isOpened(self):
        return True

    def set(self, *_):
        pass

    def release(self):
        pass


@pytest.fixture(autouse=True)
def recording_capture(monkeypatch):
    RecordingCapture.opened = []
    monkeypatch.setattr(cv2, "VideoCapture", RecordingCapture)


def test_opens_the_selected_camera_not_simply_number_zero():
    selection, _, store = make(names=["Iriun Webcam", "HD Webcam", "OBS Virtual Camera"])

    OpenCvFrameSource(store, selection).open()

    assert RecordingCapture.opened == [(1, cv2.CAP_DSHOW)]  # the laptop camera, not the phone driver at 0


def test_opens_the_camera_the_user_saved_by_name():
    selection, _, store = make(names=["Iriun Webcam", "HD Webcam"], settings=Settings(camera_name="Iriun Webcam"))

    OpenCvFrameSource(store, selection).open()

    assert RecordingCapture.opened == [(0, cv2.CAP_DSHOW)]


def test_looks_for_cameras_again_on_every_open_because_numbers_shift():
    selection, catalog, store = make(names=["Iriun Webcam", "HD Webcam"], settings=Settings(camera_name="HD Webcam"))
    source = OpenCvFrameSource(store, selection)
    source.open()
    catalog.names = ["HD Webcam"]  # the phone app closed: the laptop camera is now number 0

    source.open()

    assert RecordingCapture.opened == [(1, cv2.CAP_DSHOW), (0, cv2.CAP_DSHOW)]


def test_a_missing_saved_camera_is_reported_by_name():
    selection, _, store = make(names=["Iriun Webcam"], settings=Settings(camera_name="HD Webcam"))

    with pytest.raises(CameraError, match="HD Webcam"):
        OpenCvFrameSource(store, selection).open()
    assert RecordingCapture.opened == []


def test_no_camera_at_all_is_reported():
    selection, _, store = make(names=[])

    with pytest.raises(CameraError, match="No camera found"):
        OpenCvFrameSource(store, selection).open()
