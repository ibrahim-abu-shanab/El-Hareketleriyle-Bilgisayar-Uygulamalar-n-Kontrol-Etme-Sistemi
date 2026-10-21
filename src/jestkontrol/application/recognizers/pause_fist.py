"""Pause / resume: hold a fist for PAUSE_HOLD_S. The fist must open before it can fire again."""

from jestkontrol.application.recognizers.base import GestureContext, GestureRecognizer
from jestkontrol.domain.geometry import is_fist
from jestkontrol.domain.gestures import GestureEvent, GestureType, PauseToggled
from jestkontrol.domain.modes import OperatingMode

PAUSE_HOLD_S = 1.0


class PauseFistRecognizer(GestureRecognizer):
    gesture = GestureType.PAUSE
    modes = frozenset(OperatingMode)
    active_while_paused = True

    def __init__(self) -> None:
        self._fist_since: float | None = None
        self._fired = False

    def recognize(self, context: GestureContext) -> list[GestureEvent]:
        if not is_fist(context.hand):
            return self.reset()
        if self._fist_since is None:
            self._fist_since = context.now
        if not self._fired and context.now - self._fist_since >= PAUSE_HOLD_S:
            self._fired = True
            return [PauseToggled()]
        return []

    def reset(self) -> list[GestureEvent]:
        self._fist_since = None
        self._fired = False
        return []
