"""About: project information, how it works, privacy, team and shortcuts."""

import webbrowser

import customtkinter as ctk

from jestkontrol.ui.context import UiContext
from jestkontrol.ui.pages.base import PAGE_PADDING, Page
from jestkontrol.ui.widgets.controls import make_button
from jestkontrol.ui.widgets.surfaces import Card, KeyChip, Pill, card_header

VERSION = "0.1"
REPOSITORY_URL = "https://github.com/yasir-keles/El-Hareketleriyle-Bilgisayar-Uygulamalar-n-Kontrol-Etme-Sistemi"
TECHNOLOGIES = ("Python 3.12", "OpenCV", "MediaPipe Hands", "PyAutoGUI", "pycaw", "CustomTkinter")
# (name, is captain, role) as in the requirements report (Hafta2_Gereksinim_Analiz_Raporu.docx).
TEAM = (
    ("Muhammed Hammud Elalavi", True, "about.role.interface"),
    ("Yasir Elkeleş", False, "about.role.gestures"),
    ("İbrahim Ebu Şeneb", False, "about.role.vision"),
)
FIXED_SHORTCUTS = (
    ("Ctrl+1 … Ctrl+5", "about.shortcut.pages"),
    ("Ctrl+M", "about.shortcut.mini"),
    ("Esc", "about.shortcut.stop_test"),
)


class AboutPage(Page):
    def __init__(self, master, ctx: UiContext) -> None:
        super().__init__(master, ctx)
        self.header(ctx.t("about.title"), ctx.t("about.subtitle"))
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=PAGE_PADDING - 8, pady=(0, 12))
        self.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure((0, 1), weight=1, uniform="columns")
        self._build_identity(body)
        self._build_how_it_works(body)
        self._build_privacy(body)
        self._build_team(body)
        self._build_shortcuts(body)

    def _card(self, parent, row: int, column: int, title: str, icon: str, span: int = 1) -> Card:
        card = Card(parent, self.ctx)
        card.grid(row=row, column=column, columnspan=span, sticky="nsew", padx=8, pady=(0, 16))
        card.grid_columnconfigure(0, weight=1)
        card_header(card, self.ctx, title, icon).grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        return card

    def _text(self, parent, text: str, row: int, muted: bool = False, wrap: int = 420) -> ctk.CTkLabel:
        c = self.ctx.colors
        label = ctk.CTkLabel(
            parent, text=text, anchor="w", justify="left", wraplength=wrap, font=self.ctx.theme.font("body"),
            text_color=c.text_muted if muted else c.text_2,
        )
        label.grid(row=row, column=0, sticky="w", padx=20, pady=(0, 8))
        return label

    def _build_identity(self, body) -> None:
        ctx, c = self.ctx, self.ctx.colors
        card = Card(body, ctx)
        card.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 16))
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text="", image=ctx.theme.icon_image("hand", c.primary_text, 36), width=64, height=64, corner_radius=16, fg_color=c.primary_tint).grid(row=0, column=0, rowspan=3, padx=20, pady=20)
        ctk.CTkLabel(card, text=f"{ctx.t('app.name')}  ·  {ctx.t('about.version', version=VERSION)}", anchor="w", font=ctx.theme.font("page_title"), text_color=c.text).grid(row=0, column=1, sticky="w", pady=(18, 0))
        ctk.CTkLabel(card, text=ctx.t("about.project"), anchor="w", font=ctx.theme.font("body"), text_color=c.text_2).grid(row=1, column=1, sticky="w")
        ctk.CTkLabel(card, text=ctx.t("about.course"), anchor="w", font=ctx.theme.font("caption"), text_color=c.text_muted).grid(row=2, column=1, sticky="w", pady=(0, 6))
        badges = ctk.CTkFrame(card, fg_color="transparent")
        badges.grid(row=3, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 12))
        for name in TECHNOLOGIES:
            Pill(badges, ctx, name, "primary").pack(side="left", padx=(0, 8))
        make_button(
            card, ctx, ctx.t("about.github"), icon="external_link", command=lambda: webbrowser.open(REPOSITORY_URL)
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 18))

    def _build_how_it_works(self, body) -> None:
        ctx = self.ctx
        card = self._card(body, 1, 0, ctx.t("about.how.title"), "info")
        for index in range(1, 4):
            self._text(card, f"{index}.  {ctx.t(f'about.how.step{index}')}", index)

    def _build_privacy(self, body) -> None:
        ctx = self.ctx
        card = self._card(body, 1, 1, ctx.t("about.privacy.title"), "lock")
        self._text(card, ctx.t("about.privacy.text"), 1)

    def _build_team(self, body) -> None:
        ctx, c = self.ctx, self.ctx.colors
        card = self._card(body, 2, 0, ctx.t("about.team.title"), "people")
        for index, (name, captain, role_key) in enumerate(TEAM, start=1):
            member = ctk.CTkFrame(card, fg_color="transparent")
            member.grid(row=index, column=0, sticky="w", padx=20, pady=(0, 10))
            title = ctk.CTkFrame(member, fg_color="transparent")
            title.pack(anchor="w")
            ctk.CTkLabel(title, text=name, font=ctx.theme.font("label"), text_color=c.text, height=22).pack(side="left")
            if captain:
                Pill(title, ctx, ctx.t("about.team.captain"), "primary").pack(side="left", padx=10)
            ctk.CTkLabel(member, text=ctx.t(role_key), font=ctx.theme.font("caption"), text_color=c.text_muted, height=18).pack(anchor="w")

    def _build_shortcuts(self, body) -> None:
        ctx, c = self.ctx, self.ctx.colors
        card = self._card(body, 2, 1, ctx.t("about.shortcuts.title"), "keyboard")
        shortcuts = (*FIXED_SHORTCUTS, (str(ctx.services.emergency.current), "about.shortcut.estop"))
        for index, (keys, text_key) in enumerate(shortcuts, start=1):
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.grid(row=index, column=0, sticky="w", padx=20, pady=(0, 8))
            KeyChip(row, ctx, keys).pack(side="left")
            ctk.CTkLabel(row, text=ctx.t(text_key), font=ctx.theme.font("body"), text_color=c.text_2).pack(side="left", padx=12)
