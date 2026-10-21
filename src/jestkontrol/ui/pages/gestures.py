"""Gesture catalog: one card per gesture with its illustration and an on/off switch."""

import customtkinter as ctk
from PIL import Image

from jestkontrol.application.gesture_catalog import GestureGroup, GestureInfo, gestures_in_group
from jestkontrol.ui.context import UiContext
from jestkontrol.ui.pages.base import PAGE_PADDING, Page
from jestkontrol.ui.theme import ASSETS_DIR
from jestkontrol.ui.widgets.controls import Segmented, make_switch
from jestkontrol.ui.widgets.surfaces import Card, Pill

ART_SIZE = (200, 120)  # keeps the 440:264 aspect of the illustrations
CARD_WIDTH = 232
FILTER_ALL = "all"


class GesturesPage(Page):
    def __init__(self, master, ctx: UiContext) -> None:
        super().__init__(master, ctx)
        self._group: GestureGroup | None = None
        self._images: dict[str, ctk.CTkImage] = {}
        header, _ = self.header(ctx.t("gestures.title"), ctx.t("gestures.subtitle"))
        options = [(FILTER_ALL, ctx.t("gestures.filter.all"))] + [
            (group.value, ctx.t(f"mode.{group.value}")) for group in GestureGroup
        ]
        Segmented(header, ctx, options, FILTER_ALL, self._on_filter, height=ctx.theme.size["button"] - 4).grid(row=0, column=1, sticky="e")

        self._grid = ctk.CTkFrame(self, fg_color="transparent")
        self._grid.grid(row=1, column=0, sticky="nsew", padx=PAGE_PADDING)
        self.grid_rowconfigure(1, weight=1)
        self._grid.bind("<Configure>", lambda event: self._layout(event.width))
        self._cards: list[Card] = []
        self._columns = 0

        tip = ctk.CTkFrame(self, fg_color="transparent")
        tip.grid(row=2, column=0, sticky="w", padx=PAGE_PADDING, pady=(12, PAGE_PADDING))
        ctk.CTkLabel(tip, text=" " + ctx.t("gestures.tip"), image=ctx.theme.icon_image("tip", ctx.colors.warning_text), compound="left", font=ctx.theme.font("body"), text_color=ctx.colors.text_2).pack(anchor="w")
        self._populate()

    def _on_filter(self, value: str) -> None:
        self._group = None if value == FILTER_ALL else GestureGroup(value)
        self._populate()

    def _populate(self) -> None:
        for card in self._cards:
            card.destroy()
        self._cards = [self._build_card(info) for info in gestures_in_group(self._group)]
        self._columns = 0
        self._layout(self._grid.winfo_width())

    def _layout(self, width: int) -> None:
        columns = max(1, min(4, width // (CARD_WIDTH + 16)))
        if columns == self._columns:
            return
        self._columns = columns
        for index in range(8):
            self._grid.grid_columnconfigure(index, weight=0)
        for column in range(columns):
            self._grid.grid_columnconfigure(column, weight=1, uniform="cards")
        for index, card in enumerate(self._cards):
            card.grid(row=index // columns, column=index % columns, sticky="nsew", padx=8, pady=8)

    def _build_card(self, info: GestureInfo) -> Card:
        ctx, c = self.ctx, self.ctx.colors
        card = Card(self._grid, ctx)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="", image=self._art(info.art)).grid(row=0, column=0, columnspan=2, padx=14, pady=(14, 10))
        title = ctk.CTkFrame(card, fg_color="transparent")
        title.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16)
        title.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(title, text=ctx.t(info.name_key), anchor="w", font=ctx.theme.font("card_title"), text_color=c.text).grid(row=0, column=0, sticky="w")
        Pill(title, ctx, ctx.t(info.group_key), "primary" if info.group is not GestureGroup.GENERAL else "muted").grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(card, text=ctx.t(info.description_key), anchor="nw", justify="left", wraplength=CARD_WIDTH - 40, font=ctx.theme.font("body"), text_color=c.text_2, height=66).grid(row=2, column=0, columnspan=2, sticky="nw", padx=16, pady=(6, 4))
        enabled = self.ctx.services.settings.current.is_enabled(info.gesture)
        switch = make_switch(card, ctx, enabled, lambda value, g=info: self._set_enabled(g, value), text=ctx.t("gestures.enabled" if enabled else "gestures.disabled"))
        if info.always_on:
            switch.configure(state="disabled", text=ctx.t("gestures.always_on"), text_color=c.text_muted)
        switch.grid(row=3, column=0, sticky="w", padx=16, pady=(0, 16))
        self._switches = getattr(self, "_switches", {})
        self._switches[info.gesture] = switch
        return card

    def _art(self, name: str) -> ctk.CTkImage:
        if name not in self._images:
            image = Image.open(ASSETS_DIR / "art" / f"{name}.png")
            self._images[name] = ctk.CTkImage(light_image=image, dark_image=image, size=ART_SIZE)
        return self._images[name]

    def _set_enabled(self, info: GestureInfo, enabled: bool) -> None:
        settings = self.ctx.services.settings
        gestures = set(settings.current.enabled_gestures)
        gestures.add(info.gesture) if enabled else gestures.discard(info.gesture)
        settings.change(enabled_gestures=frozenset(gestures))
        self._switches[info.gesture].configure(text=self.ctx.t("gestures.enabled" if enabled else "gestures.disabled"))
