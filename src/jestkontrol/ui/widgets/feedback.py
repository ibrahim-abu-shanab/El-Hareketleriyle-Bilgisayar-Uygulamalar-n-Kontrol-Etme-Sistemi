"""Transient feedback: toasts below the window and modal dialogs."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import customtkinter as ctk

from jestkontrol.ui.context import UiContext
from jestkontrol.ui.widgets.controls import make_button

TOAST_DURATION_MS = 3000
TOAST_BOTTOM_MARGIN = 24
TOAST_WIDTH = 420
DIALOG_WIDTH = 480

# tone -> (icon token, accent token, tint token)
_TONES: dict[str, tuple[str, str, str]] = {
    "success": ("check", "success_text", "success_tint"),
    "info": ("export", "success_text", "success_tint"),
    "warning": ("hand", "warning_text", "warning_tint"),
    "danger": ("error", "danger_text", "danger_tint"),
}


class ToastHost:
    """Shows one toast at a time, centered near the bottom of the window, for three seconds."""

    def __init__(self, window, ctx: UiContext) -> None:
        self._window = window
        self._ctx = ctx
        self._toast: ctk.CTkFrame | None = None
        self._hide_job: str | None = None

    def show(
        self,
        text: str,
        tone: str = "success",
        action_text: str | None = None,
        action: Callable[[], None] | None = None,
    ) -> None:
        self.hide()
        c = self._ctx.colors
        icon, accent, tint = _TONES[tone]
        toast = ctk.CTkFrame(
            self._window,
            fg_color=c.card,
            border_width=1,
            border_color=c.border,
            corner_radius=self._ctx.theme.radius["tile"],
            width=TOAST_WIDTH,
        )
        glyph = self._ctx.theme.icon_image(icon, getattr(c, accent), self._ctx.theme.size["icon"]["md"])
        ctk.CTkLabel(
            toast, text="", image=glyph, width=36, height=36, corner_radius=18, fg_color=getattr(c, tint)
        ).grid(row=0, column=0, padx=(16, 12), pady=14)
        ctk.CTkLabel(
            toast,
            text=text,
            wraplength=TOAST_WIDTH - 140,
            justify="left",
            anchor="w",
            font=self._ctx.theme.font("body"),
            text_color=c.text,
        ).grid(row=0, column=1, sticky="w")
        toast.grid_columnconfigure(1, weight=1)
        if action_text and action:
            make_button(toast, self._ctx, action_text, style="link", command=action, height=32).grid(
                row=0, column=2, padx=(8, 12)
            )
        toast.place(relx=0.5, rely=1.0, y=-TOAST_BOTTOM_MARGIN, anchor="s")
        toast.lift()
        self._toast = toast
        self._hide_job = self._window.after(TOAST_DURATION_MS, self.hide)

    def hide(self) -> None:
        if self._hide_job is not None:
            self._window.after_cancel(self._hide_job)
            self._hide_job = None
        if self._toast is not None:
            self._toast.destroy()
            self._toast = None


@dataclass(frozen=True)
class DialogButton:
    label: str
    style: str = "secondary"
    action: Callable[[], None] | None = None


def open_modal(
    window, ctx: UiContext, title: str, text: str, icon: str, tone: str
) -> tuple[ctk.CTkToplevel, ctk.CTkFrame]:
    """A modal window with icon, title and explanation; the returned body's column 1 from row 2 is free."""
    c = ctx.colors
    _, accent, tint = _TONES[tone]
    dialog = ctk.CTkToplevel(window)
    dialog.title(title)
    dialog.configure(fg_color=c.card)
    dialog.resizable(False, False)
    dialog.transient(window)
    dialog.protocol("WM_DELETE_WINDOW", lambda: close_modal(dialog))

    body = ctk.CTkFrame(dialog, fg_color="transparent")
    body.pack(padx=24, pady=24)
    glyph = ctx.theme.icon_image(icon, getattr(c, accent), ctx.theme.size["icon"]["nav"])
    ctk.CTkLabel(
        body, text="", image=glyph, width=48, height=48, corner_radius=24, fg_color=getattr(c, tint)
    ).grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, 16))
    ctk.CTkLabel(
        body, text=title, font=ctx.theme.font("card_title"), text_color=c.text, anchor="w"
    ).grid(row=0, column=1, sticky="w")
    ctk.CTkLabel(
        body,
        text=text,
        font=ctx.theme.font("body"),
        text_color=c.text_2,
        wraplength=DIALOG_WIDTH - 140,
        justify="left",
        anchor="w",
    ).grid(row=1, column=1, sticky="w", pady=(6, 20))
    return dialog, body


def show_modal(window, dialog: ctk.CTkToplevel) -> None:
    """Centers the dialog over ``window`` and makes it modal."""
    dialog.update_idletasks()
    x = window.winfo_rootx() + (window.winfo_width() - dialog.winfo_reqwidth()) // 2
    y = window.winfo_rooty() + (window.winfo_height() - dialog.winfo_reqheight()) // 3
    dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")
    dialog.after(50, dialog.grab_set)


def close_modal(dialog: ctk.CTkToplevel) -> None:
    dialog.grab_release()
    dialog.destroy()


def show_dialog(
    window,
    ctx: UiContext,
    title: str,
    text: str,
    buttons: Sequence[DialogButton],
    icon: str = "error",
    tone: str = "danger",
) -> None:
    """A modal message: icon, title, explanation and action buttons (the last one is the main action)."""
    dialog, body = open_modal(window, ctx, title, text, icon, tone)
    row = ctk.CTkFrame(body, fg_color="transparent")
    row.grid(row=2, column=1, sticky="e")

    def choose(button: DialogButton) -> None:
        close_modal(dialog)
        if button.action:
            button.action()

    for button in buttons:
        make_button(
            row, ctx, button.label, style=button.style, command=lambda b=button: choose(b)
        ).pack(side="left", padx=(8, 0))
    show_modal(window, dialog)
