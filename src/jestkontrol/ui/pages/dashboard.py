"""Control panel: camera preview, system controls, live values and quick settings."""

import tkinter

import customtkinter as ctk
from PIL import ImageTk

from jestkontrol.application.diagnostics.fps_test import TARGET_FPS
from jestkontrol.application.gesture_catalog import gesture_info, gestures_in_mode
from jestkontrol.application.live_monitor import LiveSnapshot
from jestkontrol.application.system_controller import SystemStatus
from jestkontrol.domain.gestures import GestureType
from jestkontrol.domain.modes import OperatingMode, SystemState
from jestkontrol.domain.settings import SETTING_RANGES
from jestkontrol.ui.context import UiContext
from jestkontrol.ui.pages.base import PAGE_PADDING, Page
from jestkontrol.ui.preview import PreviewContent, PreviewRenderer, round_corners
from jestkontrol.ui.widgets.controls import Segmented, SliderField, make_button
from jestkontrol.ui.widgets.surfaces import Card, KeyChip, Pill, card_header, divider

RIGHT_COLUMN_WIDTH = 340
PREVIEW_FPS_INTERVAL_MS = 33
PREVIEW_IDLE_INTERVAL_MS = 250
STATS_INTERVAL_MS = 500
DEFAULT_ASPECT = 4 / 3
EVENTS_SHOWN = 3
_SUBTITLE_KEYS = {
    SystemState.OFF: "dashboard.subtitle.off",
    SystemState.PAUSED: "dashboard.subtitle.paused",
}
_STATE_TEXT = {SystemState.ACTIVE: "state.active", SystemState.PAUSED: "state.paused", SystemState.OFF: "state.off"}
_STATE_TONE = {SystemState.ACTIVE: "success", SystemState.PAUSED: "warning", SystemState.OFF: "muted"}
_MODES = (OperatingMode.MOUSE, OperatingMode.SCROLL, OperatingMode.VOLUME)


class DashboardPage(Page):
    def __init__(self, master, ctx: UiContext) -> None:
        super().__init__(master, ctx)
        self._services = ctx.services
        self._renderer = PreviewRenderer(ctx)
        self._photo: ImageTk.PhotoImage | None = None
        self._shown_state: tuple | None = None

        header, self._subtitle = self.header(ctx.t("dashboard.title"), self._subtitle_text())
        self._mini_button = make_button(
            header, ctx, ctx.t("dashboard.mini_window"), icon="mini_window", command=ctx.show_mini_window, height=ctx.theme.size["button"]
        )
        self._mini_button.grid(row=0, column=1, sticky="e")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=PAGE_PADDING, pady=(0, PAGE_PADDING))
        self.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self._build_left(body)
        self._build_right(body)

        self.listen(self._services.controller.subscribe(self.on_ui_thread(self._refresh_state)))
        self._refresh_state()
        self._refresh_stats()
        self._tick_preview()
        self.every(STATS_INTERVAL_MS, self._refresh_stats)

    # --- construction ------------------------------------------------------------------------

    def _build_left(self, body: ctk.CTkFrame) -> None:
        ctx, c = self.ctx, self.ctx.colors
        left = ctk.CTkFrame(body, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)

        card = Card(left, ctx)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        title_row = ctk.CTkFrame(card, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 10))
        title_row.grid_columnconfigure(0, weight=1)
        card_header(title_row, ctx, ctx.t("preview.title"), "video").grid(row=0, column=0, sticky="w")
        self._live_pill = Pill(title_row, ctx, "", "success")
        self._live_pill.grid(row=0, column=1, padx=(0, 10))
        self._camera_label = ctk.CTkLabel(title_row, text="", font=ctx.theme.font("caption"), text_color=c.text_muted)
        self._camera_label.grid(row=0, column=2)

        self._preview_area = ctk.CTkFrame(card, fg_color="transparent")
        self._preview_area.grid(row=1, column=0, sticky="nsew", padx=20)
        self._preview_label = tkinter.Label(self._preview_area, bd=0, highlightthickness=0)
        self._preview_label.place(relx=0.5, rely=0.5, anchor="center")

        self._chips_row = ctk.CTkFrame(card, fg_color="transparent")
        self._chips_row.grid(row=2, column=0, sticky="ew", padx=20, pady=(12, 16))
        self._chips: dict[GestureType, ctk.CTkLabel] = {}
        self._build_chips_strip()

        events = Card(left, ctx)
        events.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        events.grid_columnconfigure(1, weight=1)
        self._events_icon = ctk.CTkLabel(events, text="", image=ctx.theme.icon_image("history", c.text_muted))
        self._events_icon.grid(row=0, column=0, padx=(16, 8), pady=14)
        self._events_label = ctk.CTkLabel(events, text="", anchor="w", font=ctx.theme.font("caption"), text_color=c.text_2)
        self._events_label.grid(row=0, column=1, sticky="w")

    def _build_chips_strip(self) -> None:
        ctx, c = self.ctx, self.ctx.colors
        for child in self._chips_row.winfo_children():
            child.destroy()
        make_button(
            self._chips_row, ctx, ctx.t("preview.all_gestures"), style="link", height=30,
            command=lambda: ctx.navigate("gestures"),
        ).pack(side="right")  # packed first so a narrow window clips the chips, not the link
        ctk.CTkLabel(self._chips_row, text=ctx.t("preview.in_mode"), font=ctx.theme.font("caption"), text_color=c.text_muted).pack(side="left", padx=(0, 8))
        self._chips = {}
        for info in gestures_in_mode(self._services.controller.mode):
            chip = ctk.CTkLabel(
                self._chips_row,
                text=ctx.t(info.short_key),
                font=ctx.theme.font("caption"),
                text_color=c.text_2,
                fg_color=c.muted,
                corner_radius=15,
                padx=8,
                pady=2,
                height=28,
            )
            chip.pack(side="left", padx=(0, 6))
            self._chips[info.gesture] = chip

    def _build_right(self, body: ctk.CTkFrame) -> None:
        ctx, c = self.ctx, self.ctx.colors
        right = ctk.CTkFrame(body, fg_color="transparent", width=RIGHT_COLUMN_WIDTH)
        right.grid(row=0, column=1, sticky="ns")
        right.grid_propagate(False)
        right.grid_columnconfigure(0, weight=1)

        system = Card(right, ctx)
        system.grid(row=0, column=0, sticky="ew")
        system.grid_columnconfigure(0, weight=1)
        top = ctk.CTkFrame(system, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(12, 8))
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, text=ctx.t("system.title"), font=ctx.theme.font("card_title"), text_color=c.text).grid(row=0, column=0, sticky="w")
        self._state_pill = Pill(top, ctx, "", "muted")
        self._state_pill.grid(row=0, column=1)

        self._buttons = ctk.CTkFrame(system, fg_color="transparent")
        self._buttons.grid(row=1, column=0, sticky="ew", padx=20)
        self._buttons.grid_columnconfigure((0, 1), weight=1, uniform="buttons")

        hint = ctk.CTkFrame(system, fg_color="transparent")
        hint.grid(row=2, column=0, sticky="w", padx=20, pady=(8, 4))
        KeyChip(hint, ctx, str(ctx.services.emergency.current)).pack(side="left")
        ctk.CTkLabel(hint, text=ctx.t("system.estop_hint"), font=ctx.theme.font("caption"), text_color=c.text_muted).pack(side="left", padx=(10, 0))
        divider(system, ctx).grid(row=3, column=0, sticky="ew", padx=20, pady=(4, 8))
        ctk.CTkLabel(system, text=ctx.t("system.mode"), font=ctx.theme.font("caption"), text_color=c.text_muted).grid(row=4, column=0, sticky="w", padx=20)
        self._mode_control = Segmented(
            system, ctx, [(m.value, ctx.t(f"mode.{m.value}")) for m in _MODES], self._services.controller.mode.value,
            command=self._on_mode_chosen, button_width=(RIGHT_COLUMN_WIDTH - 64) // 3,
        )
        self._mode_control.grid(row=5, column=0, padx=20, pady=(4, 14), sticky="ew")

        live = Card(right, ctx)
        live.grid(row=1, column=0, sticky="ew", pady=12)
        live.grid_columnconfigure((0, 1), weight=1, uniform="tiles")
        head = ctk.CTkFrame(live, fg_color="transparent")
        head.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(12, 8))
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(head, text=ctx.t("live.title"), font=ctx.theme.font("card_title"), text_color=c.text).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(head, text=ctx.t("live.updates"), font=ctx.theme.font("caption"), text_color=c.text_muted).grid(row=0, column=1)
        self._tiles = {
            name: self._stat_tile(live, name, icon, row, column)
            for name, icon, row, column in (("fps", "fps", 1, 0), ("hand", "hand", 1, 1), ("gesture", "tap", 2, 0), ("latency", "latency", 2, 1))
        }

        quick = Card(right, ctx)
        quick.grid(row=2, column=0, sticky="ew")
        quick.grid_columnconfigure(0, weight=1)
        qhead = ctk.CTkFrame(quick, fg_color="transparent")
        qhead.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 2))
        qhead.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(qhead, text=ctx.t("quick.title"), font=ctx.theme.font("card_title"), text_color=c.text).grid(row=0, column=0, sticky="w")
        make_button(qhead, ctx, ctx.t("quick.all_settings"), style="link", height=32, command=lambda: ctx.navigate("settings")).grid(row=0, column=1)
        settings = self._services.settings
        self._add_quick_slider(quick, 1, "settings.sensitivity", "sensitivity", settings.current.sensitivity, ctx.translator.multiplier)
        self._add_quick_slider(quick, 2, "settings.smoothing", "smoothing_percent", settings.current.smoothing_percent, ctx.translator.percent)

    def _stat_tile(self, parent, name: str, icon: str, row: int, column: int) -> dict[str, ctk.CTkLabel]:
        ctx, c = self.ctx, self.ctx.colors
        tile = ctk.CTkFrame(parent, fg_color=c.bg, border_width=1, border_color=c.border, corner_radius=ctx.theme.radius["tile"])
        tile.grid(row=row, column=column, sticky="nsew", padx=(20 if column == 0 else 5, 5 if column == 0 else 20), pady=(0, 8 if row == 1 else 14))
        title = ctk.CTkLabel(
            tile, text=f" {ctx.t(f'stat.{name}')}", image=ctx.theme.icon_image(icon, c.text_muted, 14), compound="left",
            font=ctx.theme.font("caption"), text_color=c.text_muted, anchor="w",
        )
        title.configure(height=18)
        title.pack(anchor="w", padx=12, pady=(8, 0))
        value = ctk.CTkLabel(tile, text="", font=ctx.theme.font("stat_value"), text_color=c.text, anchor="w", height=28)
        value.pack(anchor="w", padx=12)
        detail = ctk.CTkLabel(tile, text="", font=ctx.theme.font("caption"), text_color=c.text_muted, anchor="w", height=18)
        detail.pack(anchor="w", padx=12, pady=(0, 8))
        return {"value": value, "detail": detail}

    def _add_quick_slider(self, card: Card, row: int, label_key: str, field: str, value: float, formatter) -> None:
        ctx, c = self.ctx, self.ctx.colors
        bounds = SETTING_RANGES[field]
        holder = ctk.CTkFrame(card, fg_color="transparent")
        holder.grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 4 if row == 1 else 12))
        holder.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(holder, text=ctx.t(label_key), font=ctx.theme.font("body"), text_color=c.text, anchor="w", width=92).grid(row=0, column=0, sticky="w")
        SliderField(
            holder, ctx, bounds.minimum, bounds.maximum, bounds.step, value, formatter,
            command=lambda v, name=field: self._services.settings.change(**{name: v}),
            slider_width=110, value_width=52,
        ).grid(row=0, column=1, sticky="e")

    # --- behavior ----------------------------------------------------------------------------

    def _on_mode_chosen(self, value: str) -> None:
        self._services.controller.set_mode(OperatingMode(value))
        self._build_chips_strip()

    def _subtitle_text(self) -> str:
        state = self._services.controller.state
        key = _SUBTITLE_KEYS.get(state) or f"dashboard.subtitle.{self._services.controller.mode.value}"
        return self.ctx.t(key)

    def _refresh_state(self) -> None:
        """Updates everything that depends on the system state or mode."""
        ctx, controller = self.ctx, self._services.controller
        status = controller.status
        signature = (status.state, status.mode)
        if signature == self._shown_state:
            return
        self._shown_state = signature
        self._subtitle.configure(text=self._subtitle_text())
        self._state_pill.set(ctx.t(_STATE_TEXT[status.state]), _STATE_TONE[status.state])
        live = status.state is not SystemState.OFF
        self._live_pill.set(ctx.t("preview.live") if live else ctx.t("preview.off"), "success" if live else "muted")
        if live:
            self._mini_button.grid()
        else:
            self._mini_button.grid_remove()
        self._mode_control.set(status.mode.value)
        self._build_chips_strip()
        self._rebuild_buttons(status)

    def _rebuild_buttons(self, status: SystemStatus) -> None:
        ctx, system = self.ctx, self.ctx.system
        for child in self._buttons.winfo_children():
            child.destroy()
        if status.state is SystemState.OFF:
            make_button(self._buttons, ctx, ctx.t("action.start"), icon="start", style="primary", command=system.start, height=ctx.theme.size["button"]).grid(row=0, column=0, columnspan=2, sticky="ew")
            return
        if status.state is SystemState.PAUSED:
            make_button(self._buttons, ctx, ctx.t("action.resume"), icon="start", style="secondary", command=system.toggle_pause, height=ctx.theme.size["button"]).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        else:
            make_button(self._buttons, ctx, ctx.t("action.pause"), icon="pause", style="secondary", command=system.toggle_pause, height=ctx.theme.size["button"]).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        make_button(self._buttons, ctx, ctx.t("action.stop"), icon="stop", style="danger", command=system.stop, height=ctx.theme.size["button"]).grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _refresh_stats(self) -> None:
        ctx, tr = self.ctx, self.ctx.translator
        status = self._services.controller.status
        placeholder = ctx.t("format.placeholder")
        live = status.state is not SystemState.OFF
        width, height = self._services.settings.current.resolution
        camera = self._services.camera_selection.label() or ctx.t("settings.camera.none")
        self._camera_label.configure(text=ctx.t("preview.camera_label", camera=camera, width=width, height=height))
        snapshot = self._services.monitor.snapshot()
        performance = self._services.meter.snapshot()
        tiles = self._tiles
        if not live:
            for tile in tiles.values():
                tile["value"].configure(text=placeholder)
                tile["detail"].configure(text="")
            tiles["fps"]["detail"].configure(text=ctx.t("stat.fps.target", value=int(TARGET_FPS)))
        else:
            tiles["fps"]["value"].configure(text=tr.number(performance.fps))
            tiles["fps"]["detail"].configure(text=("✓ " if performance.fps >= TARGET_FPS else "") + ctx.t("stat.fps.target", value=int(TARGET_FPS)))
            hand = snapshot.hand
            tiles["hand"]["value"].configure(text=ctx.t("stat.hand.detected" if hand else "stat.hand.none"))
            tiles["hand"]["detail"].configure(text=self._hand_detail(snapshot))
            self._show_gesture(snapshot)
            tiles["latency"]["value"].configure(text=tr.milliseconds(performance.latency_ms))
            tiles["latency"]["detail"].configure(text=ctx.t("stat.latency.detail"))
        self._refresh_events()
        self._highlight_chip(snapshot.gesture if live else None)

    def _hand_detail(self, snapshot: LiveSnapshot) -> str:
        """'Sağ el · güven %98', or just the confidence when the tracker gives no handedness."""
        hand, ctx = snapshot.hand, self.ctx
        if hand is None:
            return ""
        confidence = ctx.translator.percent(hand.confidence * 100)
        if hand.handedness is None:
            return ctx.t("stat.hand.confidence", value=confidence)
        return ctx.t("stat.hand.detail", hand=ctx.t(f"stat.hand.{hand.handedness.value}"), value=confidence)

    def _show_gesture(self, snapshot: LiveSnapshot) -> None:
        tile = self._tiles["gesture"]
        if snapshot.gesture is None:
            tile["value"].configure(text=self.ctx.t("stat.gesture.none"))
            tile["detail"].configure(text="")
        else:
            info = gesture_info(snapshot.gesture)
            tile["value"].configure(text=self.ctx.t(info.short_key))
            tile["detail"].configure(text=self.ctx.t(info.fingers_key))

    def _refresh_events(self) -> None:
        ctx, tr = self.ctx, self.ctx.translator
        events = self._services.event_log.recent(EVENTS_SHOWN)
        if not events:
            self._events_label.configure(text=f"{ctx.t('events.title')}   {ctx.t('events.empty')}")
            return
        parts = []
        for event in events:
            params = {name: ctx.t(value) for name, value in event.params.items()}
            parts.append(f"{event.at:%H:%M:%S}  {ctx.t(event.key, **params)}")
        self._events_label.configure(text=f"{ctx.t('events.title')}      " + "      ".join(parts))

    def _highlight_chip(self, active: GestureType | None) -> None:
        c = self.ctx.colors
        for gesture, chip in self._chips.items():
            chip.configure(
                fg_color=c.warning_tint if gesture is active else c.muted,
                text_color=c.warning_text if gesture is active else c.text_2,
            )

    def _tick_preview(self) -> None:
        state = self._services.controller.state
        self._draw_preview()
        interval = PREVIEW_IDLE_INTERVAL_MS if state is SystemState.OFF else PREVIEW_FPS_INTERVAL_MS
        self.schedule("preview", interval, self._tick_preview)

    def _draw_preview(self) -> None:
        area_width, area_height = self._preview_area.winfo_width(), self._preview_area.winfo_height()
        if area_width < 50 or area_height < 50:
            return
        snapshot = self._services.monitor.snapshot()
        frame = snapshot.frame
        aspect = frame.shape[1] / frame.shape[0] if frame is not None else DEFAULT_ASPECT
        width = min(area_width, int(area_height * aspect))
        size = (width, int(width / aspect))
        content = PreviewContent(snapshot, self._services.controller.status, self._services.settings.current)
        image = self._renderer.render(size, content)
        image = round_corners(image, self.ctx.theme.radius["card"], self.ctx.theme.resolve(self.ctx.colors.card))
        self._photo = ImageTk.PhotoImage(image)
        self._preview_label.configure(image=self._photo)

