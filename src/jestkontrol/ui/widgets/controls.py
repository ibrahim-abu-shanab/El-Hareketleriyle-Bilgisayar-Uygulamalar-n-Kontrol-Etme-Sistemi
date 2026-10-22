"""Interactive controls styled with the design tokens."""

from collections.abc import Callable, Sequence

import customtkinter as ctk

from jestkontrol.ui.context import UiContext


def make_button(
    master,
    ctx: UiContext,
    text: str,
    *,
    command: Callable[[], None] | None = None,
    style: str = "secondary",
    icon: str | None = None,
    width: int = 0,
    height: int | None = None,
) -> ctk.CTkButton:
    """style: primary (filled accent), secondary (outlined), danger (filled red) or link (text only)."""
    c = ctx.colors
    look = {
        "primary": dict(fg_color=c.primary, hover_color=c.primary_text, text_color=c.on_primary, border_width=0),
        "danger": dict(fg_color=c.danger, hover_color=c.danger_text, text_color=c.on_danger, border_width=0),
        "secondary": dict(
            fg_color="transparent",
            hover_color=c.muted,
            text_color=c.text,
            border_width=1,
            border_color=c.field_border,
        ),
        "link": dict(fg_color="transparent", hover_color=c.muted, text_color=c.primary_text, border_width=0),
    }[style]
    image = ctx.theme.icon_image(icon, look["text_color"]) if icon else None
    return ctk.CTkButton(
        master,
        text=text,
        image=image,
        compound="left",
        command=command,
        width=width,
        height=height or ctx.theme.size["button"],
        corner_radius=ctx.theme.radius["button"],
        font=ctx.theme.font("body"),
        **look,
    )


class Segmented(ctk.CTkFrame):
    """A row of mutually exclusive options: the selected one is filled with the accent color."""

    def __init__(
        self,
        master,
        ctx: UiContext,
        options: Sequence[tuple[str, str]],
        value: str,
        command: Callable[[str], None],
        button_width: int = 0,
        height: int | None = None,
    ) -> None:
        super().__init__(
            master, fg_color=ctx.colors.muted, corner_radius=ctx.theme.radius["button"]
        )
        self._ctx = ctx
        self._command = command
        self._buttons: dict[str, ctk.CTkButton] = {}
        for column, (option, label) in enumerate(options):
            button = ctk.CTkButton(
                self,
                text=label,
                width=button_width,
                height=height or ctx.theme.size["button"] - 8,
                corner_radius=ctx.theme.radius["field"],
                font=ctx.theme.font("body"),
                command=lambda option=option: self._choose(option),
            )
            button.grid(row=0, column=column, padx=(4, 0 if column < len(options) - 1 else 4), pady=4)
            self._buttons[option] = button
        self.set(value)

    def set(self, value: str) -> None:
        c = self._ctx.colors
        for option, button in self._buttons.items():
            if option == value:
                button.configure(fg_color=c.primary, hover_color=c.primary, text_color=c.on_primary)
            else:
                button.configure(fg_color="transparent", hover_color=c.border, text_color=c.text_2)

    def set_enabled(self, enabled: bool) -> None:
        for button in self._buttons.values():
            button.configure(state="normal" if enabled else "disabled")

    def _choose(self, value: str) -> None:
        self.set(value)
        self._command(value)


def make_switch(
    master, ctx: UiContext, value: bool, command: Callable[[bool], None], text: str = ""
) -> ctk.CTkSwitch:
    c = ctx.colors
    switch = ctk.CTkSwitch(
        master,
        text=text,
        font=ctx.theme.font("body"),
        text_color=c.text,
        progress_color=c.primary,
        fg_color=c.field_border,
        button_color=c.text,
        button_hover_color=c.text_2,
        switch_width=44,
        switch_height=24,
    )
    if value:
        switch.select()
    switch.configure(command=lambda: command(bool(switch.get())))
    return switch


class SliderField(ctk.CTkFrame):
    """A slider with its formatted value shown on the right."""

    def __init__(
        self,
        master,
        ctx: UiContext,
        minimum: float,
        maximum: float,
        step: float,
        value: float,
        formatter: Callable[[float], str],
        command: Callable[[float], None],
        slider_width: int = 200,
        value_width: int = 56,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        c = ctx.colors
        self._formatter = formatter
        self._command = command
        self._step = step
        self._slider = ctk.CTkSlider(
            self,
            from_=minimum,
            to=maximum,
            number_of_steps=max(round((maximum - minimum) / step), 1),
            width=slider_width,
            height=18,
            progress_color=c.primary,
            button_color=c.primary,
            button_hover_color=c.primary_text,
            fg_color=c.muted,
            command=self._on_change,
        )
        self._slider.set(value)
        self._slider.grid(row=0, column=0, padx=(0, 12))
        self._label = ctk.CTkLabel(
            self,
            text=formatter(value),
            width=value_width,
            anchor="e",
            font=ctx.theme.font("body"),
            text_color=c.text,
        )
        self._label.grid(row=0, column=1)

    def set(self, value: float) -> None:
        self._slider.set(value)
        self._label.configure(text=self._formatter(value))

    def _on_change(self, raw: float) -> None:
        value = round(raw / self._step) * self._step
        self._label.configure(text=self._formatter(value))
        self._command(value)


def make_dropdown(
    master,
    ctx: UiContext,
    values: Sequence[str],
    current: str,
    command: Callable[[str], None],
    width: int = 220,
) -> ctk.CTkComboBox:
    c = ctx.colors
    box = ctk.CTkComboBox(
        master,
        values=list(values),
        state="readonly",
        width=width,
        height=ctx.theme.size["button"],
        corner_radius=ctx.theme.radius["field"],
        border_width=1,
        border_color=c.field_border,
        fg_color=c.card,
        button_color=c.muted,
        button_hover_color=c.border,
        text_color=c.text,
        dropdown_fg_color=c.card,
        dropdown_text_color=c.text,
        dropdown_hover_color=c.muted,
        font=ctx.theme.font("body"),
        dropdown_font=ctx.theme.font("body"),
        command=command,
    )
    box.set(current)
    return box
