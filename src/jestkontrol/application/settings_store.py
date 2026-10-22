"""Holds the live settings; changes apply instantly to the running system and are persisted."""

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from jestkontrol.application.observable import Listeners, Unsubscribe
from jestkontrol.application.ports import SettingsRepository
from jestkontrol.domain.settings import Settings


class SettingsStore:
    def __init__(self, repository: SettingsRepository) -> None:
        self._repository = repository
        self._current = repository.load()
        self._listeners = Listeners()

    @property
    def current(self) -> Settings:
        return self._current

    def subscribe(self, listener: Callable[[Settings], None]) -> Unsubscribe:
        return self._listeners.add(listener)

    def update(self, settings: Settings) -> None:
        self._current = settings
        self._repository.save(settings)
        self._listeners.notify(settings)

    def change(self, **changes: Any) -> None:
        self.update(replace(self._current, **changes))

    def reset_to_defaults(self) -> None:
        self.update(Settings())
