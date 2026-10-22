import pytest

from jestkontrol.application.camera_selection import CameraSelection
from jestkontrol.application.settings_store import SettingsStore
from jestkontrol.domain.camera import CameraDevice, choose_camera, is_default_candidate, unique_names
from jestkontrol.domain.settings import Settings
from tests.fakes import FakeCameraCatalog
from tests.test_metrics_and_settings_store import InMemoryRepository

# The cameras of a real laptop: a phone-as-webcam driver comes first in DirectShow's order.
LAPTOP = ["Iriun Webcam", "HD Webcam", "Camera (NVIDIA Broadcast)", "OBS Virtual Camera"]


def devices(*names: str) -> list[CameraDevice]:
    return [CameraDevice(index, name) for index, name in enumerate(names)]


# --- which cameras make a good automatic choice -------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["HD Webcam", "Integrated Camera", "USB2.0 HD UVC WebCam", "Logitech C920", "HP TrueVision HD Camera",
     "FaceTime HD Camera", "OBSBOT Tiny 2"],  # OBSBOT is a real webcam: only the word "OBS" is a tool
)
def test_physical_color_cameras_are_default_candidates(name):
    assert is_default_candidate(name)


@pytest.mark.parametrize(
    "name",
    ["Iriun Webcam", "OBS Virtual Camera", "Camera (NVIDIA Broadcast)", "Integrated IR Camera",
     "Snap Camera", "DroidCam Source 3", "ManyCam Virtual Webcam", "Reincubate Camo", "EpocCam Camera"],
)
def test_virtual_and_infrared_cameras_are_not_default_candidates(name):
    assert not is_default_candidate(name)


# --- choosing a camera --------------------------------------------------------------------------


def test_automatic_choice_skips_virtual_cameras_even_when_they_come_first():
    assert choose_camera(devices(*LAPTOP), saved_name="") == CameraDevice(1, "HD Webcam")


def test_automatic_choice_falls_back_to_the_first_camera_when_all_are_virtual():
    assert choose_camera(devices("Iriun Webcam", "OBS Virtual Camera"), "") == CameraDevice(0, "Iriun Webcam")


def test_saved_name_wins_even_for_a_virtual_camera():
    assert choose_camera(devices(*LAPTOP), "Iriun Webcam") == CameraDevice(0, "Iriun Webcam")


def test_saved_camera_that_is_gone_is_not_replaced_silently():
    assert choose_camera(devices("HD Webcam"), "USB Camera") is None


def test_no_cameras_means_no_choice():
    assert choose_camera([], "") is None


def test_identical_names_are_told_apart():
    named = unique_names(devices("USB Camera", "HD Webcam", "USB Camera", "USB Camera"))

    assert [d.name for d in named] == ["USB Camera", "HD Webcam", "USB Camera (2)", "USB Camera (3)"]
    assert [d.index for d in named] == [0, 1, 2, 3]


# --- the selection service ----------------------------------------------------------------------


def make(names=LAPTOP, settings=None):
    catalog = FakeCameraCatalog(names)
    store = SettingsStore(InMemoryRepository(settings))
    return CameraSelection(catalog, store), catalog, store


def test_device_list_is_enumerated_once_until_refreshed():
    selection, catalog, _ = make()

    selection.devices()
    selection.devices()
    assert catalog.calls == 1
    selection.refresh()

    assert catalog.calls == 2


def test_selected_camera_is_the_real_one_by_default():
    selection, _, _ = make()

    assert selection.selected() == CameraDevice(1, "HD Webcam")
    assert selection.label() == "HD Webcam"


def test_selecting_a_camera_saves_its_name_not_its_number():
    selection, _, store = make()

    selection.select(selection.devices()[0])

    assert store.current.camera_name == "Iriun Webcam"
    assert selection.selected() == CameraDevice(0, "Iriun Webcam")


def test_a_saved_camera_is_found_again_even_if_its_number_changed():
    selection, catalog, _ = make(settings=Settings(camera_name="HD Webcam"))
    catalog.names = ["HD Webcam", "Iriun Webcam"]  # the phone app was closed: the order changed

    selection.refresh()

    assert selection.selected() == CameraDevice(0, "HD Webcam")


def test_when_the_saved_camera_disappears_nothing_is_selected_but_its_name_is_still_shown():
    selection, catalog, _ = make(settings=Settings(camera_name="HD Webcam"))
    catalog.names = ["Iriun Webcam"]

    selection.refresh()

    assert selection.selected() is None
    assert selection.label() == "HD Webcam"


def test_label_is_empty_when_there_is_no_camera_at_all():
    selection, _, _ = make(names=[])

    assert selection.selected() is None and selection.label() == ""
