"""What every page and widget needs: services, theme, text lookup and shell actions."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from jestkontrol.application.i18n.translator import Translator
from jestkontrol.application.services import AppServices
from jestkontrol.ui.dispatcher import UiDispatcher
from jestkontrol.ui.theme import Theme


@dataclass
class UiContext:
    services: AppServices
    theme: Theme
    dispatcher: UiDispatcher
    # shell actions, bound by the main window once it exists
    navigate: Callable[[str], None] = field(default=lambda page: None)
    toast: Callable[..., None] = field(default=lambda text, **options: None)
    dialog: Callable[..., None] = field(default=lambda **options: None)
    show_mini_window: Callable[[], None] = field(default=lambda: None)
    system: Any = None  # SystemActions, bound by the main window

    @property
    def translator(self) -> Translator:
        return self.services.translator

    def t(self, key: str, **params: object) -> str:
        return self.services.translator.t(key, **params)

    @property
    def colors(self):
        return self.theme.colors
