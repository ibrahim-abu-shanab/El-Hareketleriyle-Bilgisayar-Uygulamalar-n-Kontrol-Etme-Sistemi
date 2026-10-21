"""Click accuracy test (N2): the user is asked for a click, each answer is scored."""

import random
from dataclasses import dataclass
from enum import Enum

from jestkontrol.domain.gestures import MouseButton

TARGET_ACCURACY = 0.90
TRIAL_TIMEOUT_S = 3.0
TRIAL_COUNT_CHOICES = (10, 20, 30)
DEFAULT_TRIAL_COUNT = 20


class AccuracyGesture(Enum):
    LEFT_CLICK = "left_click"
    RIGHT_CLICK = "right_click"
    MIXED = "mixed"


class TrialOutcome(Enum):
    CORRECT = "correct"
    WRONG = "wrong"
    MISSED = "missed"


@dataclass(frozen=True, slots=True)
class WrongDetection:
    trial_number: int
    detected: MouseButton


@dataclass(frozen=True, slots=True)
class AccuracyTestResult:
    gesture: AccuracyGesture
    outcomes: tuple[TrialOutcome, ...]
    first_wrong: WrongDetection | None

    @property
    def trials(self) -> int:
        return len(self.outcomes)

    def count(self, outcome: TrialOutcome) -> int:
        return self.outcomes.count(outcome)

    @property
    def accuracy(self) -> float:
        """Correct share in [0, 1]."""
        return self.count(TrialOutcome.CORRECT) / self.trials if self.trials else 0.0

    @property
    def passed(self) -> bool:
        return self.accuracy >= TARGET_ACCURACY


class AccuracyTestSession:
    def __init__(
        self,
        gesture: AccuracyGesture,
        trials: int = DEFAULT_TRIAL_COUNT,
        rng: random.Random | None = None,
    ) -> None:
        self.gesture = gesture
        self.total_trials = trials
        self._rng = rng or random.Random()
        self._outcomes: list[TrialOutcome] = []
        self._first_wrong: WrongDetection | None = None
        self._targets = [self._pick_target() for _ in range(trials)]
        self._trial_started_at: float | None = None  # None until start(): nothing is scored before

    def start(self, now: float) -> None:
        self._trial_started_at = now

    @property
    def current_trial(self) -> int:
        """1-based number of the trial being asked for (total_trials once finished)."""
        return min(len(self._outcomes) + 1, self.total_trials)

    @property
    def current_target(self) -> MouseButton | None:
        return None if self.is_finished else self._targets[len(self._outcomes)]

    @property
    def is_finished(self) -> bool:
        return len(self._outcomes) >= self.total_trials

    @property
    def outcomes(self) -> tuple[TrialOutcome, ...]:
        return tuple(self._outcomes)

    def seconds_left(self, now: float) -> float:
        if self._trial_started_at is None:
            return TRIAL_TIMEOUT_S
        return max(TRIAL_TIMEOUT_S - (now - self._trial_started_at), 0.0)

    def on_click(self, button: MouseButton, now: float) -> None:
        target = self.current_target
        if target is None or self._trial_started_at is None:
            return
        if button is target:
            self._finish_trial(TrialOutcome.CORRECT, now)
        else:
            self._first_wrong = self._first_wrong or WrongDetection(self.current_trial, button)
            self._finish_trial(TrialOutcome.WRONG, now)

    def tick(self, now: float) -> None:
        """Marks the current trial missed once its time is up."""
        if self._trial_started_at is not None and not self.is_finished and self.seconds_left(now) == 0:
            self._finish_trial(TrialOutcome.MISSED, now)

    def result(self) -> AccuracyTestResult:
        return AccuracyTestResult(self.gesture, tuple(self._outcomes), self._first_wrong)

    def _finish_trial(self, outcome: TrialOutcome, now: float) -> None:
        self._outcomes.append(outcome)
        self._trial_started_at = now

    def _pick_target(self) -> MouseButton:
        match self.gesture:
            case AccuracyGesture.LEFT_CLICK:
                return MouseButton.LEFT
            case AccuracyGesture.RIGHT_CLICK:
                return MouseButton.RIGHT
            case AccuracyGesture.MIXED:
                return self._rng.choice(list(MouseButton))
