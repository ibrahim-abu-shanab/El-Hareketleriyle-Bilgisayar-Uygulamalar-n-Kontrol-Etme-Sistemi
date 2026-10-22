"""Runs the recognizers that are relevant for the current mode, state and settings."""

from collections.abc import Iterable, Sequence

from jestkontrol.application.recognizers.base import GestureContext, GestureRecognizer
from jestkontrol.domain.gestures import GestureEvent
from jestkontrol.domain.landmarks import HandFrame
from jestkontrol.domain.modes import OperatingMode, SystemState
from jestkontrol.domain.settings import Settings


class GestureEngine:
    def __init__(self, recognizers: Sequence[GestureRecognizer]) -> None:
        self._recognizers = tuple(recognizers)
        self._active: list[GestureRecognizer] = []

    def process(
        self,
        hand: HandFrame | None,
        now: float,
        settings: Settings,
        mode: OperatingMode,
        state: SystemState,
    ) -> list[GestureEvent]:
        selected = [r for r in self._recognizers if _is_active(r, settings, mode, state)]
        events = self._reset_all(r for r in self._active if r not in selected)
        self._active = selected
        if hand is None:
            return events + self._reset_all(selected)
        context = GestureContext(hand, now, settings)
        for recognizer in selected:
            events.extend(recognizer.recognize(context))
        return events

    def release_all(self) -> list[GestureEvent]:
        """Close every in-progress gesture (e.g. when the system stops)."""
        events = self._reset_all(self._active)
        self._active = []
        return events

    @staticmethod
    def _reset_all(recognizers: Iterable[GestureRecognizer]) -> list[GestureEvent]:
        events: list[GestureEvent] = []
        for recognizer in recognizers:
            events.extend(recognizer.reset())
        return events


def _is_active(
    recognizer: GestureRecognizer,
    settings: Settings,
    mode: OperatingMode,
    state: SystemState,
) -> bool:
    if state is SystemState.OFF:
        return False
    if state is SystemState.PAUSED and not recognizer.active_while_paused:
        return False
    return mode in recognizer.modes and settings.is_enabled(recognizer.gesture)
