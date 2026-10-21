"""What the user-facing gestures are, how they are grouped, and which events they produce."""

from dataclasses import dataclass
from enum import Enum

from jestkontrol.domain.gestures import (
    Clicked,
    CursorMoved,
    DragStarted,
    GestureEvent,
    GestureType,
    MouseButton,
    PauseToggled,
    Scrolled,
    VolumeSet,
)
from jestkontrol.domain.modes import OperatingMode
from jestkontrol.domain.settings import ALWAYS_ENABLED_GESTURES


class GestureGroup(Enum):
    MOUSE = "mouse"
    SCROLL = "scroll"
    VOLUME = "volume"
    GENERAL = "general"


@dataclass(frozen=True, slots=True)
class GestureInfo:
    gesture: GestureType
    group: GestureGroup
    art: str

    @property
    def always_on(self) -> bool:
        return self.gesture in ALWAYS_ENABLED_GESTURES

    @property
    def name_key(self) -> str:
        return f"gesture.{self.gesture.value}.name"

    @property
    def short_key(self) -> str:
        return f"gesture.{self.gesture.value}.short"

    @property
    def description_key(self) -> str:
        return f"gesture.{self.gesture.value}.desc"

    @property
    def fingers_key(self) -> str:
        return f"gesture.{self.gesture.value}.fingers"

    @property
    def group_key(self) -> str:
        return f"mode.{self.group.value}"


GESTURE_CATALOG: tuple[GestureInfo, ...] = (
    GestureInfo(GestureType.MOVE, GestureGroup.MOUSE, "g_move"),
    GestureInfo(GestureType.LEFT_CLICK, GestureGroup.MOUSE, "g_left"),
    GestureInfo(GestureType.RIGHT_CLICK, GestureGroup.MOUSE, "g_right"),
    GestureInfo(GestureType.DRAG, GestureGroup.MOUSE, "g_drag"),
    GestureInfo(GestureType.SCROLL, GestureGroup.SCROLL, "g_scroll"),
    GestureInfo(GestureType.VOLUME, GestureGroup.VOLUME, "g_volume"),
    GestureInfo(GestureType.PAUSE, GestureGroup.GENERAL, "g_pause"),
)

_GROUP_OF_MODE: dict[OperatingMode, GestureGroup] = {
    OperatingMode.MOUSE: GestureGroup.MOUSE,
    OperatingMode.SCROLL: GestureGroup.SCROLL,
    OperatingMode.VOLUME: GestureGroup.VOLUME,
}


def gesture_info(gesture: GestureType) -> GestureInfo:
    return next(info for info in GESTURE_CATALOG if info.gesture is gesture)


def gestures_in_mode(mode: OperatingMode) -> tuple[GestureInfo, ...]:
    group = _GROUP_OF_MODE[mode]
    return tuple(info for info in GESTURE_CATALOG if info.group is group)


def gestures_in_group(group: GestureGroup | None) -> tuple[GestureInfo, ...]:
    """All gestures when ``group`` is None."""
    return tuple(info for info in GESTURE_CATALOG if group is None or info.group is group)


def gesture_of(event: GestureEvent) -> GestureType | None:
    """The gesture that produced an event (for display)."""
    match event:
        case CursorMoved():
            return GestureType.MOVE
        case Clicked(button=MouseButton.LEFT):
            return GestureType.LEFT_CLICK
        case Clicked(button=MouseButton.RIGHT):
            return GestureType.RIGHT_CLICK
        case DragStarted():
            return GestureType.DRAG
        case Scrolled():
            return GestureType.SCROLL
        case VolumeSet():
            return GestureType.VOLUME
        case PauseToggled():
            return GestureType.PAUSE
    return None
