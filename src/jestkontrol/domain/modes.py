"""Operating mode and system lifecycle state."""

from enum import Enum


class OperatingMode(Enum):
    MOUSE = "mouse"
    SCROLL = "scroll"
    VOLUME = "volume"


class SystemState(Enum):
    OFF = "off"
    ACTIVE = "active"
    PAUSED = "paused"
