"""Settings persisted as a JSON file; missing or unknown keys fall back to defaults."""

import json
import logging
from collections.abc import Callable
from dataclasses import fields
from enum import Enum
from pathlib import Path
from typing import Any

from jestkontrol.domain.appearance import Language, ThemeMode
from jestkontrol.domain.gestures import GestureType
from jestkontrol.domain.settings import Settings
from jestkontrol.domain.shortcut import Shortcut

logger = logging.getLogger(__name__)


class JsonSettingsRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> Settings:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return Settings()
        except (OSError, json.JSONDecodeError):
            logger.warning("Settings file %s is unreadable; using defaults", self._path)
            return Settings()
        return _from_dict(data) if isinstance(data, dict) else Settings()

    def save(self, settings: Settings) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(_to_dict(settings), indent=2, ensure_ascii=False), encoding="utf-8"
        )


# How stored JSON values become Settings values (the inverse of _encode).
_DECODERS: dict[str, Callable[[Any], Any]] = {
    "resolution": tuple,
    "enabled_gestures": lambda values: frozenset(GestureType(v) for v in values),
    "language": Language,
    "theme": ThemeMode,
    "emergency_shortcut": Shortcut.parse,
}


def _encode(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Shortcut):
        return str(value)
    if isinstance(value, (set, frozenset)):
        return sorted(_encode(item) for item in value)
    if isinstance(value, tuple):
        return list(value)
    return value


def _to_dict(settings: Settings) -> dict[str, Any]:
    return {field.name: _encode(getattr(settings, field.name)) for field in fields(settings)}


def _from_dict(data: dict[str, Any]) -> Settings:
    known = {field.name for field in fields(Settings)}
    values = {name: value for name, value in data.items() if name in known}
    try:
        decoded = {name: _DECODERS.get(name, lambda v: v)(value) for name, value in values.items()}
        return Settings(**decoded)
    except (TypeError, ValueError):
        logger.warning("Settings file contains invalid values; using defaults")
        return Settings()
