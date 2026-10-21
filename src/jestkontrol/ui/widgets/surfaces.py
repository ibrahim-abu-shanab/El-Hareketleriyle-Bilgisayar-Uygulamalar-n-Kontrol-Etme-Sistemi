"""Containers and badges: cards, headers, status pills, keyboard-key chips."""

import customtkinter as ctk

from jestkontrol.ui.context import UiContext

# tone -> (background token, text token)
_PILL_TONES: dict[str, tuple[str, str]] = {
    "success": ("success_tint", "success_text"),
    "warning": ("warning_tint", "warning_text"),
    "danger": ("danger_tint", "danger_text"),
    "primary": ("primary_tint", "primary_text"),
    "muted": ("muted", "text_muted"),
}
CARD_PADDING = 20


class Card(ctk.CTkFrame):
    def __init__(self, master, ctx: UiContext, **options) -> None:
        super().__init__(
            master,
            fg_color=ctx.colors.card,
            border_width=1,
            border_color=ctx.colors.border,
            corner_radius=ctx.theme.radius["card"],
            **options,
        )


def card_header(parent, ctx: UiContext, title: str, icon: str | None = None) -> ctk.CTkFrame:
    """Icon + title on the left; the returned row's right side is free for a trailing widget."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.grid_columnconfigure(1, weight=1)
    if icon:
        glyph = ctx.theme.icon_image(icon, ctx.colors.text, ctx.theme.size["icon"]["nav"])
        ctk.CTkLabel(row, text="", image=glyph).grid(row=0, column=0, padx=(0, 10))
    ctk.CTkLabel(
        row, text=title, font=ctx.theme.font("card_title"), text_color=ctx.colors.text, anchor="w"
    ).grid(row=0, column=1, sticky="w")
    return row


class Pill(ctk.CTkLabel):
    """A rounded status badge such as AKTİF / DURAKLATILDI / KAPALI."""

    def __init__(self, master, ctx: UiContext, text: str = "", tone: str = "success") -> None:
        super().__init__(
            master,
            text=text,
            font=ctx.theme.font("label"),
            corner_radius=ctx.theme.size["icon"]["nav"],
            padx=12,
            pady=4,
        )
        self._ctx = ctx
        self.set(text, tone)

    def set(self, text: str, tone: str) -> None:
        background, foreground = _PILL_TONES[tone]
        colors = self._ctx.colors
        self.configure(
            text=text,
            fg_color=getattr(colors, background),
            text_color=getattr(colors, foreground),
        )


class KeyChip(ctk.CTkFrame):
    """A keyboard shortcut shown like a key cap, e.g. Ctrl+Alt+G."""

    def __init__(self, master, ctx: UiContext, text: str) -> None:
        super().__init__(
            master,
            fg_color=ctx.colors.card,
            border_width=1,
            border_color=ctx.colors.field_border,
            corner_radius=ctx.theme.radius["field"],
        )
        ctk.CTkLabel(
            self, text=text, font=ctx.theme.font("kbd"), text_color=ctx.colors.text, padx=8, pady=0, height=22
        ).pack(padx=2, pady=2)


def divider(parent, ctx: UiContext) -> ctk.CTkFrame:
    return ctk.CTkFrame(parent, height=1, fg_color=ctx.colors.border)
