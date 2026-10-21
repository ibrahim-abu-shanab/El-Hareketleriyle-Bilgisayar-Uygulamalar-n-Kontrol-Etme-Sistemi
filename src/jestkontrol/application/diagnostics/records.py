"""Finished diagnostics as plain, storable records (what the history table and CSV export show)."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from jestkontrol.application.diagnostics.accuracy_test import AccuracyTestResult, TrialOutcome
from jestkontrol.application.diagnostics.fps_test import FpsTestResult
from jestkontrol.domain.settings import Settings

Scalar = str | int | float | bool | None


class DiagnosticKind(Enum):
    FPS = "fps"
    ACCURACY = "accuracy"


@dataclass(frozen=True, slots=True)
class DiagnosticRecord:
    recorded_at: datetime
    kind: DiagnosticKind
    passed: bool
    parameters: dict[str, Scalar] = field(default_factory=dict)
    metrics: dict[str, Scalar] = field(default_factory=dict)
    series: tuple[float, ...] = ()  # FPS per second, for the chart


def fps_record(result: FpsTestResult, settings: Settings, at: datetime) -> DiagnosticRecord:
    width, height = settings.resolution
    return DiagnosticRecord(
        at,
        DiagnosticKind.FPS,
        result.passed,
        parameters={"duration_s": result.duration_s, "width": width, "height": height},
        metrics={
            "average": round(result.average, 1),
            "minimum": result.minimum,
            "maximum": result.maximum,
            "share_above_target": round(result.share_above_target, 3),
        },
        series=result.per_second,
    )


def accuracy_record(result: AccuracyTestResult, at: datetime) -> DiagnosticRecord:
    wrong = result.first_wrong
    return DiagnosticRecord(
        at,
        DiagnosticKind.ACCURACY,
        result.passed,
        parameters={"gesture": result.gesture.value, "trials": result.trials},
        metrics={
            "correct": result.count(TrialOutcome.CORRECT),
            "wrong": result.count(TrialOutcome.WRONG),
            "missed": result.count(TrialOutcome.MISSED),
            "accuracy": round(result.accuracy, 3),
            "first_wrong_trial": wrong.trial_number if wrong else None,
            "first_wrong_detected": wrong.detected.value if wrong else None,
        },
    )
