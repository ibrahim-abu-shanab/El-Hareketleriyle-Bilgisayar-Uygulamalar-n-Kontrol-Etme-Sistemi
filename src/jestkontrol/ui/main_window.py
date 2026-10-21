"""The application shell: sidebar navigation, page area, toasts, dialogs, shortcuts and the mini window."""

import customtkinter as ctk

from jestkontrol.application.services import AppServices
from jestkontrol.domain.appearance import Language, ThemeMode
from jestkontrol.domain.modes import SystemState
from jestkontrol.domain.settings import Settings
from jestkontrol.ui.context import UiContext
from jestkontrol.ui.dispatcher import UiDispatcher
from jestkontrol.ui.mini_window import MiniWindow
from jestkontrol.ui.pages.about import AboutPage
from jestkontrol.ui.pages.base import Page
from jestkontrol.ui.pages.dashboard import DashboardPage
from jestkontrol.ui.pages.diagnostics import DiagnosticsPage
from jestkontrol.ui.pages.gestures import GesturesPage
from jestkontrol.ui.pages.settings import SettingsPage
from jestkontrol.ui.system_actions import SystemActions
from jestkontrol.ui.theme import Theme
from jestkontrol.ui.widgets.controls import Segmented, make_button
from jestkontrol.ui.widgets.feedback import ToastHost, show_dialog
from jestkontrol.ui.widgets.surfaces import KeyChip, divider

# page id -> (page class, nav icon token, translation key)
PAGES: dict[str, tuple[type[Page], str, str]] = {
    "dashboard": (DashboardPage, "dashboard", "nav.dashboard"),
    "gestures": (GesturesPage, "gestures", "nav.gestures"),
    "settings": (SettingsPage, "settings", "nav.settings"),
    "tests": (DiagnosticsPage, "tests", "nav.tests"),
    "about": (AboutPage, "about", "nav.about"),
}
SIDEBAR_WIDTH = 232
WINDOW_SIZE = (1280, 768)
WINDOW_MIN_SIZE = (1100, 680)


class MainWindow(ctk.CTk):
    def __init__(self, services: AppServices) -> None:
        settings = services.settings.current
        self._apply_appearance(settings, force=True)
        super().__init__()
        self.title(services.translator.t("app.name"))
        self.geometry("{}x{}".format(*WINDOW_SIZE))
        self.minsize(*WINDOW_MIN_SIZE)

        self._services = services
        self._ctx = UiContext(services, Theme(), UiDispatcher(self))
        self.configure(fg_color=self._ctx.colors.bg)
        self._current_page = "dashboard"
        self._page: Page | None = None
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._shown_settings = settings

        self._toasts = ToastHost(self, self._ctx)
        self._ctx.navigate = self.navigate
        self._ctx.toast = self._toasts.show
        self._ctx.dialog = self._show_dialog
        self._ctx.show_mini_window = self.show_mini_window
        self._ctx.system = SystemActions(self._ctx)
        self._mini = MiniWindow(self, self._ctx, self.show_main_window)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)
        self._sidebar: ctk.CTkFrame | None = None
        self._build_sidebar()
        self.navigate(self._current_page)

        services.settings.subscribe(lambda updated: self._ctx.dispatcher.post(self._on_settings_changed, updated))
        services.controller.subscribe(lambda status: self._ctx.dispatcher.post(self._on_status_changed))
        services.presence.subscribe(lambda: self._post_toast("toast.no_hand", tone="warning"))
        services.diagnostics.on_finished(lambda: self._post_toast("toast.test_finished"))
        self._bind_shortcuts()
        self._start_hotkey()
        self.protocol("WM_DELETE_WINDOW", self._close)

    # --- navigation and shell ----------------------------------------------------------------

    def navigate(self, page_id: str) -> None:
        self._current_page = page_id
        if self._page is not None:
            self._page.destroy()
        page_class = PAGES[page_id][0]
        self._page = page_class(self._content, self._ctx)
        self._page.grid(row=0, column=0, sticky="nsew")
        self._highlight_nav()

    def _build_sidebar(self) -> None:
        ctx, c = self._ctx, self._ctx.colors
        if self._sidebar is not None:
            self._sidebar.destroy()
        sidebar = ctk.CTkFrame(self, width=SIDEBAR_WIDTH, fg_color=c.nav, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(2, weight=1)
        self._sidebar = sidebar

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="w", padx=20, pady=(24, 22))
        ctk.CTkLabel(brand, text="", image=ctx.theme.icon_image("hand", c.primary_text, 24), width=44, height=44, corner_radius=12, fg_color=c.primary_tint).grid(row=0, column=0, rowspan=2, padx=(0, 12))
        ctk.CTkLabel(brand, text=ctx.t("app.name"), anchor="w", font=ctx.theme.font("card_title"), text_color=c.text).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(brand, text=ctx.t("app.tagline"), anchor="w", font=ctx.theme.font("caption"), text_color=c.text_muted).grid(row=1, column=1, sticky="w")

        nav = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav.grid(row=1, column=0, sticky="ew", padx=12)
        nav.grid_columnconfigure(0, weight=1)
        self._nav_buttons = {}
        for row, (page_id, (_, icon, key)) in enumerate(PAGES.items()):
            button = ctk.CTkButton(
                nav, text=f"  {ctx.t(key)}", image=ctx.theme.icon_image(icon, c.text_2, ctx.theme.size["icon"]["nav"]),
                compound="left", anchor="w", height=ctx.theme.size["nav_item"], corner_radius=ctx.theme.radius["button"],
                fg_color="transparent", hover_color=c.muted, text_color=c.text_2, font=ctx.theme.font("body"),
                command=lambda page_id=page_id: self.navigate(page_id),
            )
            button.grid(row=row, column=0, sticky="ew", pady=3)
            self._nav_buttons[page_id] = button

        footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        divider(footer, ctx).grid(row=0, column=0, columnspan=2, sticky="ew")
        estop = ctk.CTkFrame(footer, fg_color="transparent")
        estop.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(14, 8))
        ctk.CTkLabel(estop, text=ctx.t("sidebar.estop"), font=ctx.theme.font("caption"), text_color=c.text_muted).pack(side="left")
        KeyChip(estop, ctx, str(self._services.emergency.current)).pack(side="right")
        controls = ctk.CTkFrame(footer, fg_color="transparent")
        controls.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 20))
        controls.grid_columnconfigure(0, weight=1)
        Segmented(
            controls, ctx, [(Language.TURKISH.value, "TR"), (Language.ENGLISH.value, "EN")], self._services.settings.current.language.value,
            command=lambda value: self._services.settings.change(language=Language(value)), button_width=44, height=32,
        ).grid(row=0, column=0, sticky="w")
        make_button(controls, ctx, "", icon=self._theme_icon(), command=self._toggle_theme, width=40, height=40).grid(row=0, column=1, sticky="e")
        self._highlight_nav()

    def _highlight_nav(self) -> None:
        c = self._ctx.colors
        for page_id, button in self._nav_buttons.items():
            selected = page_id == self._current_page
            button.configure(fg_color=c.muted if selected else "transparent", text_color=c.text if selected else c.text_2)

    def _theme_icon(self) -> str:
        return "theme_light" if ctk.get_appearance_mode() == "Dark" else "theme_dark"

    def _toggle_theme(self) -> None:
        dark = ctk.get_appearance_mode() == "Dark"
        self._services.settings.change(theme=ThemeMode.LIGHT if dark else ThemeMode.DARK)

    def _post_toast(self, key: str, tone: str = "success") -> None:
        """Safe from any thread: the text is looked up when the toast is shown, in the current language."""
        self._ctx.dispatcher.post(lambda: self._ctx.toast(self._ctx.t(key), tone=tone))

    def _show_dialog(self, **options) -> None:
        show_dialog(self, self._ctx, **options)

    # --- reacting to changes -----------------------------------------------------------------

    @staticmethod
    def _apply_appearance(settings: Settings, force: bool = False) -> None:
        ctk.set_appearance_mode(settings.theme.value)
        ctk.set_widget_scaling(settings.ui_scale_percent / 100)
        ctk.set_window_scaling(settings.ui_scale_percent / 100)

    def _on_settings_changed(self, settings: Settings) -> None:
        previous, self._shown_settings = self._shown_settings, settings
        appearance_changed = (previous.theme, previous.ui_scale_percent) != (settings.theme, settings.ui_scale_percent)
        language_changed = previous.language is not settings.language
        shortcut_changed = previous.emergency_shortcut != settings.emergency_shortcut
        if appearance_changed:
            self._apply_appearance(settings)
        if appearance_changed or language_changed or shortcut_changed:
            self.configure(fg_color=self._ctx.colors.bg)
            self.title(self._services.translator.t("app.name"))
            self._build_sidebar()
            self.navigate(self._current_page)
            self._mini.destroy()
            self._mini = MiniWindow(self, self._ctx, self.show_main_window)

    def _on_status_changed(self) -> None:
        if self._services.controller.state is SystemState.OFF and self._mini.winfo_viewable():
            self.show_main_window()

    # --- mini window and lifecycle -----------------------------------------------------------

    def show_mini_window(self) -> None:
        self.withdraw()
        self._mini.show()

    def show_main_window(self) -> None:
        self._mini.hide()
        self.deiconify()
        self.lift()
        self.focus_force()

    def _bind_shortcuts(self) -> None:
        for index, page_id in enumerate(PAGES, start=1):
            self.bind(f"<Control-Key-{index}>", lambda _, page_id=page_id: self.navigate(page_id))
        self.bind("<Control-m>", lambda _: self._open_mini_if_running())
        self.bind("<Escape>", lambda _: self._services.diagnostics.cancel())

    def _open_mini_if_running(self) -> None:
        if self._services.controller.state is not SystemState.OFF:
            self.show_mini_window()

    def _start_hotkey(self) -> None:
        try:
            self._services.emergency.activate(lambda: self._ctx.dispatcher.post(self._ctx.system.toggle_running))
        except OSError:
            self._ctx.toast(self._ctx.t("toast.hotkey_unavailable"), tone="warning")

    def _close(self) -> None:
        self._services.shutdown()
        self.destroy()
