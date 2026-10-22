"""Tests and performance: FPS test, click-accuracy test, history and CSV export."""

import os
from pathlib import Path

import customtkinter as ctk

from jestkontrol.application.diagnostics.accuracy_test import (
    DEFAULT_TRIAL_COUNT,
    TARGET_ACCURACY,
    TRIAL_COUNT_CHOICES,
    TRIAL_TIMEOUT_S,
    AccuracyGesture,
    TrialOutcome,
)
from jestkontrol.application.diagnostics.fps_test import (
    DEFAULT_DURATION_S,
    DURATION_CHOICES_S,
    TARGET_FPS,
)
from jestkontrol.application.diagnostics.records import DiagnosticKind, DiagnosticRecord
from jestkontrol.domain.gestures import MouseButton
from jestkontrol.ui.context import UiContext
from jestkontrol.ui.pages.base import PAGE_PADDING, Page
from jestkontrol.ui.widgets.charts import FpsChart
from jestkontrol.ui.widgets.controls import Segmented, make_button, make_dropdown
from jestkontrol.ui.widgets.feedback import DialogButton
from jestkontrol.ui.widgets.surfaces import Card, Pill, card_header, divider

REFRESH_MS = 200
HISTORY_ROWS_SHOWN = 8
EXPORT_FILE_NAME = "jestkontrol_sonuclar.csv"
DOT_SIZE = 30
DOTS_PER_ROW = 10
_ACCURACY_OPTIONS = tuple(AccuracyGesture)


def export_folder() -> Path:
    documents = Path.home() / "Documents"
    return documents if documents.is_dir() else Path.home()


class DiagnosticsPage(Page):
    def __init__(self, master, ctx: UiContext) -> None:
        super().__init__(master, ctx)
        self._diagnostics = ctx.services.diagnostics
        self._history = ctx.services.history
        self._duration = DEFAULT_DURATION_S
        self._accuracy_gesture = AccuracyGesture.LEFT_CLICK
        self._trial_count = DEFAULT_TRIAL_COUNT
        self._dots: list[ctk.CTkLabel] = []
        self._dots_total = 0
        self._locked: tuple[bool, bool] | None = None  # (fps running, accuracy running) last applied

        header, _ = self.header(ctx.t("tests.title"), ctx.t("tests.subtitle"))
        make_button(header, ctx, ctx.t("tests.export"), icon="export", style="primary", command=self._export, height=ctx.theme.size["button_large"]).grid(row=0, column=1, sticky="e")

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=PAGE_PADDING - 8, pady=(0, 12))
        self.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure((0, 1), weight=1, uniform="cards")
        self._build_fps_card(body)
        self._build_accuracy_card(body)
        self._build_history_card(body)
        self.listen(self._history.subscribe(self.on_ui_thread(self._rebuild_history)))
        self._rebuild_history()
        self._refresh()
        self.every(REFRESH_MS, self._refresh)

    # --- FPS card ----------------------------------------------------------------------------

    def _build_fps_card(self, body) -> None:
        ctx, c = self.ctx, self.ctx.colors
        card = Card(body, ctx)
        card.grid(row=0, column=0, sticky="nsew", padx=8, pady=(0, 16))
        card.grid_columnconfigure(0, weight=1)
        head = card_header(card, ctx, ctx.t("tests.fps.title"), "fps")
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 4))
        self._fps_pill = Pill(head, ctx, "", "muted")
        self._fps_pill.grid(row=0, column=2)
        self._fps_summary = ctk.CTkLabel(card, text="", anchor="w", font=ctx.theme.font("caption"), text_color=c.text_muted)
        self._fps_summary.grid(row=1, column=0, sticky="w", padx=20)

        controls = ctk.CTkFrame(card, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew", padx=20, pady=12)
        controls.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(controls, text=ctx.t("tests.fps.duration"), font=ctx.theme.font("caption"), text_color=c.text_muted).grid(row=0, column=0, padx=(0, 10))
        self._duration_control = Segmented(
            controls, ctx, [(str(d), ctx.t("format.seconds", value=d)) for d in DURATION_CHOICES_S], str(self._duration),
            command=lambda value: setattr(self, "_duration", int(value)), height=ctx.theme.size["button"] - 8,
        )
        self._duration_control.grid(row=0, column=1, sticky="w")
        self._fps_button_slot = ctk.CTkFrame(controls, fg_color="transparent")
        self._fps_button_slot.grid(row=0, column=2, sticky="e")
        self._fps_button_state: tuple | None = None

        self._fps_tiles = self._tile_row(card, 3, ["tests.fps.average", "tests.fps.minimum", "tests.fps.maximum", "tests.fps.above_target"])
        self._fps_progress = ctk.CTkProgressBar(card, height=6, progress_color=c.primary, fg_color=c.muted)
        self._fps_progress.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 4))
        ctk.CTkLabel(card, text=ctx.t("tests.fps.chart_title"), anchor="w", font=ctx.theme.font("label"), text_color=c.text_muted).grid(row=5, column=0, sticky="w", padx=20, pady=(8, 0))
        self._chart = FpsChart(card, ctx)
        self._chart.grid(row=6, column=0, sticky="ew", padx=20, pady=(4, 18))

    # --- accuracy card -----------------------------------------------------------------------

    def _build_accuracy_card(self, body) -> None:
        ctx, c = self.ctx, self.ctx.colors
        card = Card(body, ctx)
        card.grid(row=0, column=1, sticky="nsew", padx=8, pady=(0, 16))
        card.grid_columnconfigure(0, weight=1)
        head = card_header(card, ctx, ctx.t("tests.accuracy.title"), "hand")
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 4))
        self._acc_pill = Pill(head, ctx, "", "muted")
        self._acc_pill.grid(row=0, column=2)
        self._acc_summary = ctk.CTkLabel(card, text="", anchor="w", font=ctx.theme.font("caption"), text_color=c.text_muted)
        self._acc_summary.grid(row=1, column=0, sticky="w", padx=20)

        controls = ctk.CTkFrame(card, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew", padx=20, pady=12)
        self._gesture_control = Segmented(
            controls, ctx, [(g.value, self._gesture_label(g)) for g in _ACCURACY_OPTIONS], self._accuracy_gesture.value,
            command=lambda value: setattr(self, "_accuracy_gesture", AccuracyGesture(value)), height=ctx.theme.size["button"] - 8,
        )
        self._gesture_control.grid(row=0, column=0, sticky="w")
        self._trials_box = make_dropdown(
            controls, ctx, [ctx.t("tests.accuracy.trials_option", count=n) for n in TRIAL_COUNT_CHOICES],
            ctx.t("tests.accuracy.trials_option", count=self._trial_count),
            command=lambda label: setattr(self, "_trial_count", int(label.split()[0])), width=150,
        )
        self._trials_box.grid(row=0, column=1, padx=10)
        self._acc_button_slot = ctk.CTkFrame(card, fg_color="transparent")
        self._acc_button_slot.grid(row=7, column=0, sticky="ew", padx=20, pady=(0, 18))
        self._acc_button_state: tuple | None = None

        self._run_panel = ctk.CTkFrame(card, fg_color=c.bg, corner_radius=ctx.theme.radius["tile"])
        self._run_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self._run_panel, text=ctx.t("tests.accuracy.do_now"), anchor="w", font=ctx.theme.font("caption"), text_color=c.text_muted).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 0))
        self._target_label = ctk.CTkLabel(self._run_panel, text="", anchor="w", font=ctk.CTkFont(family="Segoe UI Semibold", size=28), text_color=c.text)
        self._target_label.grid(row=1, column=0, sticky="w", padx=16)
        self._trial_label = ctk.CTkLabel(self._run_panel, text="", anchor="w", font=ctx.theme.font("body"), text_color=c.text_2)
        self._trial_label.grid(row=2, column=0, sticky="w", padx=16)
        timer = ctk.CTkFrame(self._run_panel, fg_color="transparent")
        timer.grid(row=3, column=0, sticky="ew", padx=16, pady=(8, 14))
        timer.grid_columnconfigure(0, weight=1)
        self._countdown = ctk.CTkProgressBar(timer, height=6, progress_color=c.primary, fg_color=c.muted)
        self._countdown.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self._time_left = ctk.CTkLabel(timer, text="", font=ctx.theme.font("caption"), text_color=c.text_2)
        self._time_left.grid(row=0, column=1)
        self._dots_frame = ctk.CTkFrame(card, fg_color="transparent")

        self._acc_tiles = self._tile_row(card, 5, ["tests.accuracy.correct", "tests.accuracy.wrong", "tests.accuracy.missed", "tests.accuracy.accuracy"])
        self._acc_note = ctk.CTkLabel(card, text=ctx.t("tests.accuracy.rules"), anchor="w", justify="left", wraplength=360, font=ctx.theme.font("caption"), text_color=c.text_muted)
        self._acc_note.grid(row=6, column=0, sticky="w", padx=20, pady=(0, 12))

    def _gesture_label(self, gesture: AccuracyGesture) -> str:
        return self.ctx.t("tests.accuracy.mixed" if gesture is AccuracyGesture.MIXED else f"gesture.{gesture.value}.short")

    def _tile_row(self, card: Card, row: int, keys: list[str]) -> list[ctk.CTkLabel]:
        ctx, c = self.ctx, self.ctx.colors
        holder = ctk.CTkFrame(card, fg_color="transparent")
        holder.grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 12))
        holder.grid_columnconfigure(tuple(range(len(keys))), weight=1, uniform="tile")
        values = []
        for column, key in enumerate(keys):
            tile = ctk.CTkFrame(holder, fg_color=c.bg, border_width=1, border_color=c.border, corner_radius=ctx.theme.radius["tile"])
            tile.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 4, 0 if column == len(keys) - 1 else 4))
            value = ctk.CTkLabel(tile, text="", anchor="w", font=ctx.theme.font("stat_value"), text_color=c.text)
            value.pack(anchor="w", padx=12, pady=(8, 0))
            ctk.CTkLabel(tile, text=ctx.t(key), anchor="w", font=ctx.theme.font("caption"), text_color=c.text_muted).pack(anchor="w", padx=12, pady=(0, 8))
            values.append(value)
        return values

    # --- history card ------------------------------------------------------------------------

    def _build_history_card(self, body) -> None:
        ctx, c = self.ctx, self.ctx.colors
        self._history_card = Card(body, ctx)
        self._history_card.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0, 16))
        self._history_card.grid_columnconfigure(0, weight=1)
        head = card_header(self._history_card, ctx, ctx.t("tests.history.title"), "history")
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        self._count_label = ctk.CTkLabel(head, text="", font=ctx.theme.font("caption"), text_color=c.text_muted)
        self._count_label.grid(row=0, column=2, padx=(0, 12))
        make_button(head, ctx, ctx.t("tests.history.clear"), style="link", height=32, command=self._confirm_clear).grid(row=0, column=3)
        self._table = ctk.CTkFrame(self._history_card, fg_color="transparent")
        self._table.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 16))
        self._table.grid_columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="cols")

    def _rebuild_history(self) -> None:
        ctx, c, tr = self.ctx, self.ctx.colors, self.ctx.translator
        for child in self._table.winfo_children():
            child.destroy()
        records = self._history.records()
        self._count_label.configure(text=ctx.t("tests.history.count", count=len(records)))
        for column, key in enumerate(["when", "test", "parameters", "result", "status"]):
            ctk.CTkLabel(self._table, text=ctx.t(f"tests.history.{key}"), anchor="w", font=ctx.theme.font("label"), text_color=c.text_muted).grid(row=0, column=column, sticky="w", pady=(0, 8))
        if not records:
            ctk.CTkLabel(self._table, text=ctx.t("tests.history.empty"), anchor="w", font=ctx.theme.font("body"), text_color=c.text_2).grid(row=1, column=0, columnspan=5, sticky="w", pady=12)
            return
        for index, record in enumerate(records[:HISTORY_ROWS_SHOWN], start=1):
            divider(self._table, ctx).grid(row=index * 2 - 1, column=0, columnspan=5, sticky="ew")
            cells = [tr.date_time(record.recorded_at), ctx.t(f"tests.history.kind.{record.kind.value}"), self._parameters_text(record), self._result_text(record)]
            for column, text in enumerate(cells):
                weight = ctx.theme.font("label") if column in (1, 3) else ctx.theme.font("body")
                ctk.CTkLabel(self._table, text=text, anchor="w", font=weight, text_color=c.text if column in (1, 3) else c.text_2).grid(row=index * 2, column=column, sticky="w", pady=12)
            Pill(self._table, ctx, ctx.t("tests.history.passed" if record.passed else "tests.history.failed"), "success" if record.passed else "danger").grid(row=index * 2, column=4, sticky="w")

    def _parameters_text(self, record: DiagnosticRecord) -> str:
        p, ctx = record.parameters, self.ctx
        if record.kind is DiagnosticKind.FPS:
            return f"{ctx.t('format.seconds', value=p['duration_s'])} · {p['width']} × {p['height']}"
        return f"{self._gesture_label(AccuracyGesture(p['gesture']))} · {ctx.t('tests.accuracy.trials_option', count=p['trials'])}"

    def _result_text(self, record: DiagnosticRecord) -> str:
        ctx, tr, m = self.ctx, self.ctx.translator, record.metrics
        if record.kind is DiagnosticKind.FPS:
            return ctx.t("tests.history.result.fps", fps=tr.number(m["average"]))
        return ctx.t("tests.history.result.accuracy", percent=tr.percent(m["accuracy"] * 100), correct=m["correct"], total=record.parameters["trials"])

    # --- live refresh ------------------------------------------------------------------------

    def _refresh(self) -> None:
        self._lock_controls_while_running()
        self._refresh_fps()
        self._refresh_accuracy()

    def _lock_controls_while_running(self) -> None:
        """A running test's options cannot change under it."""
        running = (self._diagnostics.fps_session is not None, self._diagnostics.accuracy_session is not None)
        if running == self._locked:
            return
        self._locked = running
        fps_running, accuracy_running = running
        self._duration_control.set_enabled(not fps_running)
        self._gesture_control.set_enabled(not accuracy_running)
        self._trials_box.configure(state="disabled" if accuracy_running else "readonly")

    def _refresh_fps(self) -> None:
        ctx, tr, runner = self.ctx, self.ctx.translator, self._diagnostics
        session = runner.fps_session
        self._set_run_button(self._fps_button_slot, "_fps_button_state", session is not None, self._start_fps, ctx.t("tests.run_again" if self._history.latest(DiagnosticKind.FPS) else "tests.run"))
        if session is not None:
            now = ctx.services.clock.now()
            elapsed = int(session.progress(now) * session.duration_s)
            values = session.result().per_second[:elapsed]
            self._fps_pill.set(ctx.t("tests.status.running"), "primary")
            self._fps_summary.configure(text=ctx.t("tests.needs_camera"))
            self._fps_progress.set(session.progress(now))
            self._chart.update_data(values, session.duration_s, TARGET_FPS)
            if values:
                self._set_tiles(self._fps_tiles, [tr.number(sum(values) / len(values)), tr.number(min(values)), tr.number(max(values)), tr.percent(100 * sum(v >= TARGET_FPS for v in values) / len(values))])
            return
        self._fps_progress.set(0)
        record = self._history.latest(DiagnosticKind.FPS)
        if record is None:
            self._fps_pill.set(ctx.t("tests.status.none"), "muted")
            self._fps_summary.configure(text=ctx.t("tests.needs_camera"))
            self._set_tiles(self._fps_tiles, [ctx.t("format.placeholder")] * 4)
            self._chart.update_data((), self._duration, TARGET_FPS)
            return
        self._fps_pill.set(ctx.t("tests.status.passed" if record.passed else "tests.status.failed"), "success" if record.passed else "danger")
        p, m = record.parameters, record.metrics
        self._fps_summary.configure(text=ctx.t("tests.fps.summary", duration=ctx.t("format.seconds", value=p["duration_s"]), width=p["width"], height=p["height"], when=tr.relative_day_time(record.recorded_at), target=int(TARGET_FPS)))
        self._set_tiles(self._fps_tiles, [tr.number(m["average"]), tr.number(m["minimum"]), tr.number(m["maximum"]), tr.percent(m["share_above_target"] * 100)])
        self._chart.update_data(record.series, p["duration_s"], TARGET_FPS)

    def _refresh_accuracy(self) -> None:
        ctx, tr, runner = self.ctx, self.ctx.translator, self._diagnostics
        session = runner.accuracy_session
        self._set_run_button(self._acc_button_slot, "_acc_button_state", session is not None, self._start_accuracy, ctx.t("tests.run_again" if self._history.latest(DiagnosticKind.ACCURACY) else "tests.run"))
        if session is not None:
            self._show_running_panel(session)
            outcomes = session.outcomes
            correct, wrong, missed = (outcomes.count(TrialOutcome.CORRECT), outcomes.count(TrialOutcome.WRONG), outcomes.count(TrialOutcome.MISSED))
            share = 100 * correct / len(outcomes) if outcomes else 0
            self._acc_pill.set(ctx.t("tests.status.running"), "primary")
            self._acc_summary.configure(text=ctx.t("tests.needs_camera"))
            self._set_tiles(self._acc_tiles, [str(correct), str(wrong), str(missed), tr.percent(share)])
            return
        self._hide_running_panel()
        record = self._history.latest(DiagnosticKind.ACCURACY)
        if record is None:
            self._acc_pill.set(ctx.t("tests.status.none"), "muted")
            self._acc_summary.configure(text=ctx.t("tests.needs_camera"))
            self._set_tiles(self._acc_tiles, [ctx.t("format.placeholder")] * 4)
            self._acc_note.configure(text=ctx.t("tests.accuracy.rules"))
            return
        p, m = record.parameters, record.metrics
        self._acc_pill.set(ctx.t("tests.status.passed" if record.passed else "tests.status.failed"), "success" if record.passed else "danger")
        self._acc_summary.configure(text=ctx.t("tests.accuracy.summary", gesture=self._gesture_label(AccuracyGesture(p["gesture"])), trials=p["trials"], when=tr.relative_day_time(record.recorded_at), target=tr.percent(TARGET_ACCURACY * 100)))
        self._set_tiles(self._acc_tiles, [str(m["correct"]), str(m["wrong"]), str(m["missed"]), tr.percent(m["accuracy"] * 100)])
        if m.get("first_wrong_trial"):
            detected = ctx.t(f"event.{m['first_wrong_detected']}_click").lower()
            self._acc_note.configure(text=ctx.t("tests.accuracy.wrong_note", trial=m["first_wrong_trial"], detected=detected))
        else:
            self._acc_note.configure(text=ctx.t("tests.accuracy.rules"))

    def _show_running_panel(self, session) -> None:
        ctx, tr = self.ctx, self.ctx.translator
        self._run_panel.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 12))
        self._dots_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 12))
        target = session.current_target
        if target is not None:
            self._target_label.configure(text=ctx.t("event.left_click" if target is MouseButton.LEFT else "event.right_click"))
        self._trial_label.configure(text=ctx.t("tests.accuracy.trial_of", current=session.current_trial, total=session.total_trials))
        left = session.seconds_left(ctx.services.clock.now())
        self._countdown.set(left / TRIAL_TIMEOUT_S)
        self._time_left.configure(text=ctx.t("tests.accuracy.time_left", seconds=tr.number(left)))
        self._update_dots(session)

    def _hide_running_panel(self) -> None:
        self._run_panel.grid_remove()
        self._dots_frame.grid_remove()

    def _update_dots(self, session) -> None:
        c = self.ctx.colors
        if self._dots_total != session.total_trials:
            for dot in self._dots:
                dot.destroy()
            self._dots = []
            for index in range(session.total_trials):
                dot = ctk.CTkLabel(self._dots_frame, text=str(index + 1), width=DOT_SIZE, height=DOT_SIZE, corner_radius=DOT_SIZE // 2, font=self.ctx.theme.font("caption"))
                dot.grid(row=index // DOTS_PER_ROW, column=index % DOTS_PER_ROW, padx=3, pady=3)
                self._dots.append(dot)
            self._dots_total = session.total_trials
        outcomes = session.outcomes
        for index, dot in enumerate(self._dots):
            if index < len(outcomes):
                outcome = outcomes[index]
                symbol, background, foreground = {
                    TrialOutcome.CORRECT: ("✓", c.success_tint, c.success_text),
                    TrialOutcome.WRONG: ("✕", c.danger_tint, c.danger_text),
                    TrialOutcome.MISSED: ("–", c.warning_tint, c.warning_text),
                }[outcome]
                dot.configure(text=symbol, fg_color=background, text_color=foreground)
            elif index == len(outcomes):
                dot.configure(text=str(index + 1), fg_color=c.primary_tint, text_color=c.primary_text)
            else:
                dot.configure(text=str(index + 1), fg_color=c.muted, text_color=c.text_muted)

    @staticmethod
    def _set_tiles(tiles: list[ctk.CTkLabel], values: list[str]) -> None:
        for label, value in zip(tiles, values):
            label.configure(text=value)

    def _set_run_button(self, slot: ctk.CTkFrame, state_attr: str, running: bool, start, run_text: str) -> None:
        if getattr(self, state_attr) == (running, run_text):
            return
        setattr(self, state_attr, (running, run_text))
        for child in slot.winfo_children():
            child.destroy()
        ctx = self.ctx
        if running:
            make_button(slot, ctx, ctx.t("tests.stop"), icon="stop", command=self._diagnostics.cancel, height=ctx.theme.size["button"]).pack(fill="x")
        else:
            make_button(slot, ctx, run_text, icon="refresh", command=start, height=ctx.theme.size["button"]).pack(fill="x")

    # --- actions -----------------------------------------------------------------------------

    def _start_fps(self) -> None:
        self.ctx.system.run_with_camera(lambda: self._diagnostics.start_fps_test(self._duration))

    def _start_accuracy(self) -> None:
        self.ctx.system.run_with_camera(lambda: self._diagnostics.start_accuracy_test(self._accuracy_gesture, self._trial_count))

    def _confirm_clear(self) -> None:
        ctx = self.ctx
        ctx.dialog(
            title=ctx.t("dialog.clear_history.title"),
            text=ctx.t("dialog.clear_history.text"),
            buttons=[DialogButton(ctx.t("action.cancel")), DialogButton(ctx.t("dialog.clear_history.confirm"), "danger", self._history.clear)],
            icon="error",
            tone="danger",
        )

    def _export(self) -> None:
        ctx = self.ctx
        if not self._history.records():
            ctx.toast(ctx.t("toast.export_empty"), tone="warning")
            return
        path = export_folder() / EXPORT_FILE_NAME
        try:
            self._history.export(path)
        except OSError as error:
            ctx.toast(ctx.t("toast.export_failed", reason=error.strerror or str(error)), tone="danger")
            return
        ctx.toast(ctx.t("toast.exported", file=path.name), tone="info", action_text=ctx.t("action.open_folder"), action=lambda: os.startfile(path.parent))
