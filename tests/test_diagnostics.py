import random
from datetime import datetime
from pathlib import Path

import pytest

from jestkontrol.application.diagnostics.accuracy_test import (
    TRIAL_TIMEOUT_S,
    AccuracyGesture,
    AccuracyTestSession,
    TrialOutcome,
)
from jestkontrol.application.diagnostics.fps_test import TARGET_FPS, FpsTestSession
from jestkontrol.application.diagnostics.history import DiagnosticsHistory
from jestkontrol.application.diagnostics.records import (
    DiagnosticKind,
    DiagnosticRecord,
    accuracy_record,
    fps_record,
)
from jestkontrol.application.diagnostics.runner import DiagnosticsRunner
from jestkontrol.application.frame_processor import FrameResult
from jestkontrol.application.system_controller import SystemController
from jestkontrol.domain.gestures import Clicked, MouseButton
from jestkontrol.domain.modes import OperatingMode, SystemState
from jestkontrol.domain.settings import Settings
from tests.fakes import FakeClock, FakeSettingsProvider

LEFT, RIGHT = MouseButton.LEFT, MouseButton.RIGHT
MOMENT = datetime(2026, 10, 14, 14, 52)


# --- FPS test ----------------------------------------------------------------------------------


def run_fps(frames_per_second: list[int], duration: int | None = None) -> FpsTestSession:
    session = FpsTestSession(duration or len(frames_per_second))
    for second, frames in enumerate(frames_per_second):
        for frame in range(frames):
            session.on_frame(second + frame / frames)
    return session


def test_fps_result_statistics():
    result = run_fps([30, 28, 20, 30]).result()

    assert result.per_second == (30.0, 28.0, 20.0, 30.0)
    assert (result.average, result.minimum, result.maximum) == (27.0, 20.0, 30.0)
    assert result.share_above_target == 0.75
    assert result.passed


def test_fps_below_target_fails():
    assert not run_fps([20, 22, 24]).result().passed
    assert TARGET_FPS == 25


def test_fps_progress_and_finish():
    session = FpsTestSession(10)
    assert session.progress(5.0) == 0.0

    session.on_frame(100.0)

    assert session.progress(105.0) == 0.5
    assert session.seconds_left(105.0) == 5
    assert not session.is_finished(109.9)
    assert session.is_finished(110.0)


def test_frames_after_the_duration_are_not_counted():
    session = FpsTestSession(2)
    for now in (0.0, 0.5, 1.0, 2.5, 3.0):
        session.on_frame(now)

    assert session.result().per_second == (2.0, 1.0)


# --- accuracy test -----------------------------------------------------------------------------


def make_session(gesture=AccuracyGesture.LEFT_CLICK, trials=4, seed=1):
    session = AccuracyTestSession(gesture, trials, random.Random(seed))
    session.start(0.0)
    return session


def test_correct_clicks_pass_the_test():
    session = make_session()
    for index in range(4):
        session.on_click(LEFT, now=index + 1.0)

    result = session.result()

    assert session.is_finished
    assert (result.count(TrialOutcome.CORRECT), result.accuracy, result.passed) == (4, 1.0, True)


def test_wrong_button_is_counted_and_remembered_once():
    session = make_session(trials=3)

    session.on_click(LEFT, 1.0)
    session.on_click(RIGHT, 2.0)
    session.on_click(RIGHT, 3.0)

    result = session.result()
    assert result.outcomes == (TrialOutcome.CORRECT, TrialOutcome.WRONG, TrialOutcome.WRONG)
    assert (result.first_wrong.trial_number, result.first_wrong.detected) == (2, RIGHT)
    assert not result.passed


def test_trial_times_out_as_missed():
    session = make_session(trials=2)

    session.tick(TRIAL_TIMEOUT_S - 0.1)
    assert session.outcomes == ()
    session.tick(TRIAL_TIMEOUT_S)
    assert session.outcomes == (TrialOutcome.MISSED,)
    assert session.seconds_left(TRIAL_TIMEOUT_S) == TRIAL_TIMEOUT_S  # next trial restarts the clock


def test_current_trial_target_and_number():
    session = make_session(AccuracyGesture.RIGHT_CLICK, trials=2)

    assert (session.current_trial, session.current_target) == (1, RIGHT)
    session.on_click(RIGHT, 1.0)
    session.on_click(RIGHT, 2.0)

    assert (session.current_trial, session.current_target) == (2, None)


def test_mixed_test_asks_for_both_buttons():
    session = make_session(AccuracyGesture.MIXED, trials=30)
    targets = set()
    while not session.is_finished:
        targets.add(session.current_target)
        session.on_click(session.current_target, 0.0)

    assert targets == {LEFT, RIGHT}


def test_clicks_after_the_end_are_ignored():
    session = make_session(trials=1)
    session.on_click(LEFT, 1.0)
    session.on_click(RIGHT, 2.0)

    assert session.result().trials == 1


def test_ninety_percent_is_the_pass_mark():
    session = make_session(trials=10)
    for _ in range(9):
        session.on_click(LEFT, 0.0)
    session.on_click(RIGHT, 0.0)

    assert session.result().passed


# --- records and history -----------------------------------------------------------------------


class MemoryRepository:
    def __init__(self, records=None):
        self.records = list(records or [])

    def load(self):
        return list(self.records)

    def save(self, records):
        self.records = list(records)


class RecordingExporter:
    def __init__(self):
        self.calls = []

    def export(self, records, path):
        self.calls.append((list(records), path))


def make_history(records=None):
    return DiagnosticsHistory(MemoryRepository(records), RecordingExporter())


def test_fps_record_carries_settings_and_metrics():
    record = fps_record(run_fps([30, 28]).result(), Settings(resolution=(1280, 720)), MOMENT)

    assert record.kind is DiagnosticKind.FPS and record.passed
    assert record.parameters == {"duration_s": 2, "width": 1280, "height": 720}
    assert record.metrics["average"] == 29.0
    assert record.series == (30.0, 28.0)


def test_accuracy_record_carries_counts():
    session = make_session(trials=2)
    session.on_click(LEFT, 1.0)
    session.on_click(RIGHT, 2.0)

    record = accuracy_record(session.result(), MOMENT)

    assert record.kind is DiagnosticKind.ACCURACY and not record.passed
    assert record.parameters == {"gesture": "left_click", "trials": 2}
    assert (record.metrics["correct"], record.metrics["wrong"], record.metrics["accuracy"]) == (1, 1, 0.5)
    assert (record.metrics["first_wrong_trial"], record.metrics["first_wrong_detected"]) == (2, "right")


def test_history_lists_newest_first_persists_and_notifies():
    history = make_history()
    notified = []
    history.subscribe(lambda: notified.append(True))
    older = DiagnosticRecord(datetime(2026, 10, 13), DiagnosticKind.FPS, True)
    newer = DiagnosticRecord(datetime(2026, 10, 14), DiagnosticKind.ACCURACY, False)

    history.add(older)
    history.add(newer)

    assert history.records() == [newer, older]
    assert history._repository.records == [newer, older]
    assert history.latest(DiagnosticKind.FPS) == older
    assert len(notified) == 2


def test_history_loads_sorted_and_can_be_cleared():
    older = DiagnosticRecord(datetime(2026, 10, 13), DiagnosticKind.FPS, True)
    newer = DiagnosticRecord(datetime(2026, 10, 14), DiagnosticKind.FPS, True)
    history = make_history([older, newer])

    assert history.records() == [newer, older]
    history.clear()
    assert history.records() == [] and history.latest(DiagnosticKind.FPS) is None


def test_history_export_delegates_and_counts():
    history = make_history([DiagnosticRecord(MOMENT, DiagnosticKind.FPS, True)])

    count = history.export(Path("out.csv"))

    assert count == 1
    assert history._exporter.calls[0][1] == Path("out.csv")


# --- runner ------------------------------------------------------------------------------------


class Starter:
    def __init__(self):
        self.starts = 0

    def start(self):
        self.starts += 1


def make_runner():
    clock = FakeClock()
    controller = SystemController()
    starter = Starter()
    history = make_history()
    runner = DiagnosticsRunner(
        starter, controller, FakeSettingsProvider(), history, clock, now=lambda: MOMENT
    )
    return runner, clock, controller, starter, history


def frame(runner, events=()):
    runner.on_frame(object(), FrameResult(None, tuple(events)))


def test_fps_test_runs_to_completion_and_is_recorded():
    runner, clock, _, starter, history = make_runner()
    finished = []
    runner.on_finished(lambda: finished.append(True))

    runner.start_fps_test(2)
    assert runner.is_running and starter.starts == 1
    for _ in range(100):  # 100 frames over 2.5 s
        frame(runner)
        clock.advance(0.025)

    assert not runner.is_running and finished == [True]
    [record] = history.records()
    assert record.kind is DiagnosticKind.FPS
    assert record.parameters["duration_s"] == 2 and len(record.series) == 2


def test_accuracy_test_scores_clicks_forces_mouse_mode_and_resumes():
    runner, clock, controller, _, history = make_runner()
    controller.start()
    controller.set_mode(OperatingMode.VOLUME)
    controller.pause()

    runner.start_accuracy_test(AccuracyGesture.LEFT_CLICK, 2)
    assert controller.mode is OperatingMode.MOUSE and controller.state is SystemState.ACTIVE
    clock.advance(1.0)
    frame(runner, [Clicked(LEFT)])
    clock.advance(1.0)
    frame(runner, [Clicked(RIGHT)])

    assert not runner.is_running
    [record] = history.records()
    assert record.kind is DiagnosticKind.ACCURACY
    assert (record.metrics["correct"], record.metrics["wrong"]) == (1, 1)
    assert (record.metrics["first_wrong_trial"], record.metrics["first_wrong_detected"]) == (2, "right")


def test_accuracy_test_marks_silence_as_missed():
    runner, clock, _, _, history = make_runner()
    runner.start_accuracy_test(AccuracyGesture.RIGHT_CLICK, 1)

    clock.advance(TRIAL_TIMEOUT_S + 0.1)
    frame(runner)

    assert history.records()[0].metrics["missed"] == 1


def test_cancel_stops_without_recording():
    runner, _, _, _, history = make_runner()
    runner.start_fps_test(10)

    runner.cancel()

    assert not runner.is_running and history.records() == []


def test_starting_one_test_replaces_the_other():
    runner, *_ = make_runner()
    runner.start_fps_test(10)

    runner.start_accuracy_test(AccuracyGesture.MIXED, 5)

    assert runner.fps_session is None and runner.accuracy_session is not None


def test_camera_failure_while_starting_propagates_and_no_test_runs():
    runner, _, _, starter, _ = make_runner()
    starter.start = lambda: (_ for _ in ()).throw(RuntimeError("camera"))

    with pytest.raises(RuntimeError):
        runner.start_fps_test(10)

    assert not runner.is_running


def test_nothing_is_scored_before_the_session_starts():
    session = AccuracyTestSession(AccuracyGesture.LEFT_CLICK, 2)

    session.tick(100.0)
    session.on_click(LEFT, 100.0)

    assert session.outcomes == () and session.seconds_left(100.0) == TRIAL_TIMEOUT_S
