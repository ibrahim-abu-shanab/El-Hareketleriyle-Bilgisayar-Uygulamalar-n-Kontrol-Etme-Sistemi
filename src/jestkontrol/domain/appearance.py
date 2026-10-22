"""Language and theme choices."""

from enum import Enum


class Language(Enum):
    TURKISH = "tr"
    ENGLISH = "en"


class ThemeMode(Enum):
    DARK = "dark"
    LIGHT = "light"
    SYSTEM = "system"
