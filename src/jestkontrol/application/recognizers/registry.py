"""The standard set of gesture recognizers (add a new gesture by adding it here)."""

from jestkontrol.application.recognizers.base import GestureRecognizer
from jestkontrol.application.recognizers.left_click_drag import LeftClickDragRecognizer
from jestkontrol.application.recognizers.move import MoveRecognizer
from jestkontrol.application.recognizers.pause_fist import PauseFistRecognizer
from jestkontrol.application.recognizers.right_click import RightClickRecognizer
from jestkontrol.application.recognizers.scroll import ScrollRecognizer
from jestkontrol.application.recognizers.volume import VolumeRecognizer


def create_default_recognizers() -> list[GestureRecognizer]:
    return [
        MoveRecognizer(),
        LeftClickDragRecognizer(),
        RightClickRecognizer(),
        ScrollRecognizer(),
        VolumeRecognizer(),
        PauseFistRecognizer(),
    ]
