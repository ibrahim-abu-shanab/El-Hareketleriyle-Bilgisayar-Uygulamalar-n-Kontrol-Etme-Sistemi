"""One camera frame through the pipeline: track the hand, recognize gestures, perform actions."""

from dataclasses import dataclass, replace

from jestkontrol.application.action_dispatcher import ActionDispatcher
from jestkontrol.application.gesture_engine import GestureEngine
from jestkontrol.application.ports import Clock, Frame, HandTracker, SettingsProvider
from jestkontrol.application.system_controller import SystemController
from jestkontrol.domain.gestures import GestureEvent
from jestkontrol.domain.landmarks import HandFrame


@dataclass(frozen=True, slots=True)
class FrameResult:
    hand: HandFrame | None
    events: tuple[GestureEvent, ...]


class FrameProcessor:
    def __init__(
        self,
        tracker: HandTracker,
        engine: GestureEngine,
        dispatcher: ActionDispatcher,
        controller: SystemController,
        settings: SettingsProvider,
        clock: Clock,
    ) -> None:
        self._tracker = tracker
        self._engine = engine
        self._dispatcher = dispatcher
        self._controller = controller
        self._settings = settings
        self._clock = clock

    def process(self, frame: Frame) -> FrameResult:
        settings = self._settings.current
        hand = self._tracker.detect(frame)  # tracking continues while paused (skeleton stays visible)
        hand = _real_handedness(hand, settings.mirror)
        events = self._engine.process(
            hand,
            self._clock.now(),
            settings,
            self._controller.mode,
            self._controller.state,
        )
        self._dispatcher.dispatch(events)
        return FrameResult(hand, tuple(events))

    def release(self) -> None:
        """Close in-progress gestures (e.g. release a held mouse button) before stopping."""
        self._dispatcher.dispatch(self._engine.release_all())


def _real_handedness(hand: HandFrame | None, mirrored: bool) -> HandFrame | None:
    """Trackers report handedness for a mirrored view; an unmirrored image shows the other hand."""
    if hand is None or hand.handedness is None or mirrored:
        return hand
    return replace(hand, handedness=hand.handedness.opposite())
