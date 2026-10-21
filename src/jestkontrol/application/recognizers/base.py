"""Contract shared by all gesture recognizers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from jestkontrol.domain.gestures import GestureEvent, GestureType
from jestkontrol.domain.landmarks import HandFrame
from jestkontrol.domain.modes import OperatingMode
from jestkontrol.domain.settings import Settings


@dataclass(frozen=True, slots=True)
class GestureContext:
    hand: HandFrame
    now: float
    settings: Settings


class GestureRecognizer(ABC):
    """Turns hand frames into gesture events; owns only the state of its own gesture."""

    gesture: GestureType
    modes: frozenset[OperatingMode]
    active_while_paused: bool = False

    @abstractmethod
    def recognize(self, context: GestureContext) -> list[GestureEvent]: ...

    def reset(self) -> list[GestureEvent]:
        """Abandon any in-progress gesture (hand lost, mode changed); may emit closing events."""
        return []
