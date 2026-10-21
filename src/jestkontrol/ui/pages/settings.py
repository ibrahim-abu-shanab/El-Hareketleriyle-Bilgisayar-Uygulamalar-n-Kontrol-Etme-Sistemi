"""Settings: every change applies immediately and is saved automatically."""

import threading
from collections.abc import Callable

import customtkinter as ctk

from jestkontrol.domain.appearance import Language, ThemeMode
from jestkontrol.domain.gestures import GestureType
from jestkontrol.domain.settings import RESOLUTION_CHOICES, SETTING_RANGES, UI_SCALE_CHOICES
from jestkontrol.ui.context import UiContext
from jestkontrol.ui.pages.base import PAGE_PADDING, Page
from jestkontrol.ui.widgets.controls import Segmented, SliderField, make_button, make_dropdown, make_switch
from jestkontrol.ui.widgets.feedback import DialogButton
from jestkontrol.ui.widgets.setting_row import SettingRow
from jestkontrol.ui.widgets.shortcut_dialog import show_shortcut_dialog
from jestkontrol.ui.widgets.surfaces import Card, KeyChip, card_header

_THEME_OPTIONS = (ThemeMode.DARK, ThemeMode.LIGHT, ThemeMode.SYSTEM)


def _resolution_text(resolution: tuple[int, int]) -> str:
    return f"{resolution[0]} × {resolution[1]}"


class SettingsPage(Page):
    def __init__(self, master, ctx: UiContext) -> None:
        super().__init__(master, ctx)
        self._services = ctx.services
        self._settings = ctx.services.settings
        header, _ = self.header(ctx.t("settings.title"), ctx.t("settings.subtitle"))
        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(
            actions, text=" " + ctx.t("settings.saved"), image=ctx.theme.icon_image("check", ctx.colors.success_text),
            compound="left", font=ctx.theme.font("body"), text_color=ctx.colors.success_text,
        ).pack(side="left", padx=(0, 16))
        make_button(actions, ctx, ctx.t("settings.reset"), icon="reset", command=self._confirm_reset, height=ctx.theme.size["button_large"]).pack(side="left")

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=PAGE_PADDING - 8, pady=(0, 12))
        self.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure((0, 1), weight=1, uniform="columns")
        left = ctk.CTkFrame(body, fg_color="transparent")
        left.grid(row=0, column=0, sticky="new", padx=8)
        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="new", padx=8)
        for column in (left, right):
            column.grid_columnconfigure(0, weight=1)

        self._camera_row = self._build_camera_card(left)
        self._build_cursor_card(left)
        self._build_detection_card(right)
        self._build_general_card(right)
        self._load_cameras_in_background()

    # --- cards -------------------------------------------------------------------------------

    def _card(self, parent, title_key: str, icon: str, row: int) -> Card:
        card = Card(parent, self.ctx)
        card.grid(row=row, column=0, sticky="ew", pady=(0, 16))
        card.grid_columnconfigure(0, weight=1)
        card_header(card, self.ctx, self.ctx.t(title_key), icon).grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 4))
        return card

    def _row(self, card: Card, index: int, label: str, last: bool = False) -> SettingRow:
        row = SettingRow(card, self.ctx, self.ctx.t(f"settings.{label}"), self.ctx.t(f"settings.{label}.hint"), with_divider=not last)
        row.grid(row=index, column=0, sticky="ew", padx=20)
        return row

    def _build_camera_card(self, parent) -> SettingRow:
        ctx, current = self.ctx, self._settings.current
        card = self._card(parent, "settings.section.camera", "camera", 0)
        camera_row = self._row(card, 1, "camera")
        self._camera_box = make_dropdown(camera_row.control_slot, ctx, [self._camera_name(current.camera_index)], self._camera_name(current.camera_index), self._on_camera, width=170)
        self._camera_box.pack()
        resolution_row = self._row(card, 2, "resolution")
        make_dropdown(resolution_row.control_slot, ctx, [_resolution_text(r) for r in RESOLUTION_CHOICES], _resolution_text(current.resolution), self._on_resolution, width=170).pack()
        mirror_row = self._row(card, 3, "mirror")
        self._switch(mirror_row, current.mirror, lambda value: self._settings.change(mirror=value))
        skeleton_row = self._row(card, 4, "skeleton", last=True)
        self._switch(skeleton_row, current.show_skeleton, lambda value: self._settings.change(show_skeleton=value))
        return camera_row

    def _build_cursor_card(self, parent) -> None:
        current, tr = self._settings.current, self.ctx.translator
        card = self._card(parent, "settings.section.cursor", "cursor", 1)
        self._slider(self._row(card, 1, "sensitivity"), "sensitivity", current.sensitivity, tr.multiplier)
        self._slider(self._row(card, 2, "smoothing"), "smoothing_percent", current.smoothing_percent, tr.percent)
        self._slider(self._row(card, 3, "margin", last=True), "active_area_margin_percent", current.active_area_margin_percent, tr.percent)

    def _build_detection_card(self, parent) -> None:
        ctx, current, tr = self.ctx, self._settings.current, self.ctx.translator
        card = self._card(parent, "settings.section.detection", "hand", 0)
        self._slider(self._row(card, 1, "click_threshold"), "click_threshold_percent", current.click_threshold_percent, tr.percent)
        self._slider(self._row(card, 2, "click_cooldown"), "click_cooldown_ms", current.click_cooldown_ms, tr.milliseconds)
        self._switch(self._row(card, 3, "drag"), current.is_enabled(GestureType.DRAG), self._set_drag)
        self._slider(self._row(card, 4, "scroll_speed"), "scroll_speed", current.scroll_speed, lambda v: str(round(v)))
        self._slider(self._row(card, 5, "volume_sensitivity", last=True), "volume_sensitivity", current.volume_sensitivity, tr.multiplier)

    def _build_general_card(self, parent) -> None:
        ctx, current = self.ctx, self._settings.current
        card = self._card(parent, "settings.section.general", "settings", 1)
        language_row = self._row(card, 1, "language")
        Segmented(language_row.control_slot, ctx, [(l.value, ctx.t(f"language.{l.value}")) for l in Language], current.language.value, self._on_language, height=ctx.theme.size["button"] - 8).pack()
        theme_row = self._row(card, 2, "theme")
        Segmented(theme_row.control_slot, ctx, [(m.value, ctx.t(f"theme.{m.value}")) for m in _THEME_OPTIONS], current.theme.value, self._on_theme, height=ctx.theme.size["button"] - 8).pack()
        scale_row = self._row(card, 3, "ui_scale")
        make_dropdown(scale_row.control_slot, ctx, [ctx.translator.percent(s) for s in UI_SCALE_CHOICES], ctx.translator.percent(current.ui_scale_percent), self._on_scale, width=170).pack()
        estop_row = self._row(card, 4, "estop", last=True)
        KeyChip(estop_row.control_slot, ctx, str(ctx.services.emergency.current)).pack(side="left", padx=(0, 10))
        make_button(
            estop_row.control_slot, ctx, ctx.t("settings.estop.change"),
            command=lambda: show_shortcut_dialog(self.winfo_toplevel(), ctx),
        ).pack(side="left")

    # --- control helpers ---------------------------------------------------------------------

    def _slider(self, row: SettingRow, field: str, value: float, formatter: Callable[[float], str]) -> None:
        bounds = SETTING_RANGES[field]
        SliderField(
            row.control_slot, self.ctx, bounds.minimum, bounds.maximum, bounds.step, value, formatter,
            command=lambda v: self._settings.change(**{field: v}), slider_width=130, value_width=60,
        ).pack()

    def _switch(self, row: SettingRow, value: bool, command: Callable[[bool], None]) -> None:
        ctx = self.ctx

        def apply(on: bool) -> None:
            switch.configure(text=ctx.t("settings.on" if on else "settings.off"))
            command(on)

        switch = make_switch(row.control_slot, ctx, value, apply, text=ctx.t("settings.on" if value else "settings.off"))
        switch.pack()

    # --- handlers ----------------------------------------------------------------------------

    def _camera_name(self, index: int) -> str:
        return self.ctx.t("camera.name", number=index + 1)

    def _load_cameras_in_background(self) -> None:
        current = self._settings.current.camera_index

        def probe() -> None:
            indices = self._services.cameras.available_indices(keep=current)
            self.on_ui_thread(lambda: self._fill_cameras(indices))()

        threading.Thread(target=probe, name="camera-probe", daemon=True).start()

    def _fill_cameras(self, indices: list[int]) -> None:
        self._camera_box.configure(values=[self._camera_name(i) for i in indices])

    def _on_camera(self, label: str) -> None:
        index = int(label.rsplit(" ", 1)[-1]) - 1
        self._settings.change(camera_index=index)
        self.ctx.system.restart_if_running()

    def _on_resolution(self, label: str) -> None:
        width, height = (int(part) for part in label.split("×"))
        self._settings.change(resolution=(width, height))
        self.ctx.system.restart_if_running()

    def _set_drag(self, enabled: bool) -> None:
        gestures = set(self._settings.current.enabled_gestures)
        gestures.add(GestureType.DRAG) if enabled else gestures.discard(GestureType.DRAG)
        self._settings.change(enabled_gestures=frozenset(gestures))

    def _on_language(self, value: str) -> None:
        self._settings.change(language=Language(value))

    def _on_theme(self, value: str) -> None:
        self._settings.change(theme=ThemeMode(value))

    def _on_scale(self, label: str) -> None:
        self._settings.change(ui_scale_percent=int(label.strip("%")))

    def _confirm_reset(self) -> None:
        ctx = self.ctx
        ctx.dialog(
            title=ctx.t("dialog.reset.title"),
            text=ctx.t("dialog.reset.text"),
            buttons=[
                DialogButton(ctx.t("action.cancel")),
                DialogButton(ctx.t("settings.reset"), "danger", self._reset),
            ],
            icon="reset",
            tone="warning",
        )

    def _reset(self) -> None:
        self._settings.reset_to_defaults()
        self.ctx.toast(self.ctx.t("toast.saved"))
