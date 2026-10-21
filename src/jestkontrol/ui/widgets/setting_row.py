"""One labelled row of a settings card: title and hint on the left, the control on the right."""

import customtkinter as ctk

from jestkontrol.ui.context import UiContext
from jestkontrol.ui.widgets.surfaces import divider

HINT_WRAP = 190


class SettingRow(ctk.CTkFrame):
    def __init__(
        self, master, ctx: UiContext, title: str, hint: str, with_divider: bool = True
    ) -> None:
        super().__init__(master, fg_color="transparent")
        c = ctx.colors
        self.grid_columnconfigure(0, weight=1)
        text = ctk.CTkFrame(self, fg_color="transparent")
        text.grid(row=0, column=0, sticky="w", pady=10)
        ctk.CTkLabel(
            text, text=title, anchor="w", font=ctx.theme.font("body"), text_color=c.text
        ).pack(anchor="w")
        ctk.CTkLabel(
            text,
            text=hint,
            anchor="w",
            justify="left",
            wraplength=HINT_WRAP,
            font=ctx.theme.font("caption"),
            text_color=c.text_muted,
        ).pack(anchor="w")
        self.control_slot = ctk.CTkFrame(self, fg_color="transparent")
        self.control_slot.grid(row=0, column=1, sticky="e", padx=(16, 0))
        if with_divider:
            divider(self, ctx).grid(row=1, column=0, columnspan=2, sticky="ew")
