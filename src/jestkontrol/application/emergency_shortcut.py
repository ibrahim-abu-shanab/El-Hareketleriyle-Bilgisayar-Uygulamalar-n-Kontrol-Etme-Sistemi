"""The global emergency start/stop shortcut: registered from settings, changeable at runtime."""

from collections.abc import Callable

from jestkontrol.application.ports import HotkeyListener
from jestkontrol.application.settings_store import SettingsStore
from jestkontrol.domain.shortcut import Shortcut


class EmergencyShortcut:
    def __init__(self, listener: HotkeyListener, settings: SettingsStore) -> None:
        self._listener = listener
        self._settings = settings
        self._on_pressed: Callable[[], None] | None = None

    @property
    def current(self) -> Shortcut:
        return self._settings.current.emergency_shortcut

    def activate(self, on_pressed: Callable[[], None]) -> None:
        """Registers the saved shortcut; raises OSError if another application owns it."""
        self._on_pressed = on_pressed
        self._listener.start(self.current, on_pressed)

    def suspend(self) -> None:
        """Releases the shortcut temporarily (e.g. while the user records a new one)."""
        self._listener.stop()

    def resume(self) -> None:
        if self._on_pressed is not None:
            self._listener.start(self.current, self._on_pressed)

    def change(self, shortcut: Shortcut) -> None:
        """Switches to ``shortcut`` and saves it; on OSError the previous shortcut stays active."""
        self._listener.stop()
        if self._on_pressed is None:
            self._settings.change(emergency_shortcut=shortcut)
            return
        try:
            self._listener.start(shortcut, self._on_pressed)
        except OSError:
            self.resume()
            raise
        self._settings.change(emergency_shortcut=shortcut)

    def deactivate(self) -> None:
        self._listener.stop()
        self._on_pressed = None
