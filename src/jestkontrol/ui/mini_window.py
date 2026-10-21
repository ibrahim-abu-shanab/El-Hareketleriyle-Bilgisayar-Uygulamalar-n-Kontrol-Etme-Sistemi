"""A small always-on-top window with status and the main controls; replaces the main window while running."""

from collections.abc import Callable

import customtkinter as ctk

from jestkontrol.application.gesture_catalog import gesture_info
from jestkontrol.domain.modes import SystemState
from jestkontrol.ui.context import UiContext
from jestkontrol.ui.widgets.controls import make_button

REFRESH_MS = 500
WIDTH, HEIGHT = 420, 132
_STATE_TEXT = {SystemState.ACTIVE: "state.active", SystemState.PAUSED: "state.paused", SystemState.OFF: "state.off"}
_STATE_COLOR = {SystemState.ACTIVE: "success_text", SystemState.PAUSED: "warning_text", SystemState.OFF: "text_muted"}


class MiniWindow(ctk.CTkToplevel):
    def __init__(self, master, ctx: UiContext, on_open_main: Callable[[], None]) -> None:
        super().__init__(master, fg_color=ctx.colors.card)
        self._ctx = ctx
        self._services = ctx.services
        self._job: str | None = None
        self.title(ctx.t("app.name"))
        self.geometry(f"{WIDTH}x{HEIGHT}")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", on_open_main)
        self.withdraw()

        c = ctx.colors
        self.grid_columnconfigure(0, weight=1)
        text = ctk.CTkFrame(self, fg_color="transparent")
        text.grid(row=0, column=0, sticky="w", padx=20, pady=20)
        self._status = ctk.CTkLabel(text, text="", anchor="w", font=ctx.theme.font("card_title"))
        self._status.pack(anchor="w")
        self._detail = ctk.CTkLabel(text, text="", anchor="w", font=ctx.theme.font("body"), text_color=c.text_2)
        self._detail.pack(anchor="w")
        self._buttons = ctk.CTkFrame(self, fg_color="transparent")
        self._buttons.grid(row=0, column=1, padx=(0, 16))
        self._pause_button = self._icon_button(0, "pause", "secondary", lambda: ctx.system.toggle_pause())
        self._icon_button(1, "stop", "danger", lambda: ctx.system.stop())
        self._icon_button(2, "expand", "secondary", on_open_main)

    def _icon_button(self, column: int, icon: str, style: str, command: Callable[[], None]) -> ctk.CTkButton:
        button = make_button(self._buttons, self._ctx, "", icon=icon, style=style, command=command, width=44, height=44)
        button.grid(row=0, column=column, padx=3)
        return button

    def show(self) -> None:
        self.deiconify()
        self.lift()
        self._refresh()

    def hide(self) -> None:
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        self.withdraw()

    def _refresh(self) -> None:
        ctx, c = self._ctx, self._ctx.colors
        status = self._services.controller.status
        mode_name = ctx.t(f"mode.{status.mode.value}")
        self._status.configure(text=f"{ctx.t(_STATE_TEXT[status.state])} · {mode_name}", text_color=getattr(c, _STATE_COLOR[status.state]))
        self._detail.configure(text=self._detail_text(status.state))
        paused = status.state is SystemState.PAUSED
        icon = ctx.theme.icon_image("start" if paused else "pause", c.text)
        self._pause_button.configure(image=icon)
        self._job = self.after(REFRESH_MS, self._refresh)

    def _detail_text(self, state: SystemState) -> str:
        ctx, tr = self._ctx, self._ctx.translator
        if state is SystemState.PAUSED:
            return ctx.t("mini.paused_by_fist")
        gesture = self._services.monitor.snapshot().gesture
        fps = tr.number(self._services.meter.snapshot().fps, 0)
        label = ctx.t(gesture_info(gesture).short_key) if gesture else ctx.t("stat.gesture.none")
        return f"{label} · {fps} FPS"
