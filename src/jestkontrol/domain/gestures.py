"""Gesture identities and the events recognizers emit."""

from dataclasses import dataclass
from enum import Enum

from jestkontrol.domain.landmarks import Point


class GestureType(Enum):
    MOVE = "move"
    LEFT_CLICK = "left_click"
    RIGHT_CLICK = "right_click"
    DRAG = "drag"
    SCROLL = "scroll"
    VOLUME = "volume"
    PAUSE = "pause"


class MouseButton(Enum):
    LEFT = "left"
    RIGHT = "right"


class GestureEvent:
    """Base type of everything a recognizer can emit."""


@dataclass(frozen=True, slots=True)
class CursorMoved(GestureEvent):
    """Target cursor position normalized to the screen: x and y are in [0, 1]."""

    position: Point


@dataclass(frozen=True, slots=True)
class Clicked(GestureEvent):
    button: MouseButton


@dataclass(frozen=True, slots=True)
class DragStarted(GestureEvent):
    pass


@dataclass(frozen=True, slots=True)
class DragEnded(GestureEvent):
    pass


@dataclass(frozen=True, slots=True)
class Scrolled(GestureEvent):
    """Scroll amount in wheel notches; positive scrolls up."""

    notches: int


@dataclass(frozen=True, slots=True)
class VolumeSet(GestureEvent):
    """Absolute master volume in [0, 1]."""

    level: float


@dataclass(frozen=True, slots=True)
class PauseToggled(GestureEvent):
    pass
