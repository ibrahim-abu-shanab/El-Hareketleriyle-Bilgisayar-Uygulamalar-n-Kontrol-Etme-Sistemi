"""Hand landmark model (MediaPipe's 21-point convention)."""

from dataclasses import dataclass
from enum import Enum, IntEnum

LANDMARK_COUNT = 21


class LandmarkId(IntEnum):
    WRIST = 0
    THUMB_TIP = 4
    INDEX_MCP = 5
    INDEX_PIP = 6
    INDEX_TIP = 8
    MIDDLE_MCP = 9
    MIDDLE_PIP = 10
    MIDDLE_TIP = 12
    RING_MCP = 13
    RING_PIP = 14
    RING_TIP = 16
    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_TIP = 20


class Handedness(Enum):
    LEFT = "left"
    RIGHT = "right"

    def opposite(self) -> "Handedness":
        return Handedness.RIGHT if self is Handedness.LEFT else Handedness.LEFT


@dataclass(frozen=True, slots=True)
class Point:
    """A position normalized to the camera frame: x and y are in [0, 1]."""

    x: float
    y: float


@dataclass(frozen=True, slots=True)
class HandFrame:
    """The 21 landmarks of one detected hand in a single camera frame."""

    landmarks: tuple[Point, ...]
    confidence: float = 1.0
    handedness: Handedness | None = None

    def __post_init__(self) -> None:
        if len(self.landmarks) != LANDMARK_COUNT:
            raise ValueError(
                f"A hand needs {LANDMARK_COUNT} landmarks, got {len(self.landmarks)}"
            )

    def __getitem__(self, landmark: LandmarkId | int) -> Point:
        return self.landmarks[landmark]
