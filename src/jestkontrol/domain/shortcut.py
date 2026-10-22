"""A global keyboard shortcut such as Ctrl+Alt+G."""

import re
from dataclasses import dataclass
from enum import Enum


class Modifier(Enum):
    CTRL = "Ctrl"
    ALT = "Alt"
    SHIFT = "Shift"


_MODIFIER_ORDER = (Modifier.CTRL, Modifier.ALT, Modifier.SHIFT)
_REQUIRED_ANY = frozenset({Modifier.CTRL, Modifier.ALT})  # Shift alone would hijack normal typing
_KEY_PATTERN = re.compile(r"^(?:[A-Z0-9]|F(?:[1-9]|1[0-2]))$")


@dataclass(frozen=True, slots=True)
class Shortcut:
    modifiers: frozenset[Modifier]
    key: str

    def __post_init__(self) -> None:
        if not _KEY_PATTERN.match(self.key):
            raise ValueError(f"Unsupported shortcut key: {self.key!r}")
        if not self.modifiers & _REQUIRED_ANY:
            raise ValueError("A global shortcut needs Ctrl or Alt")

    @classmethod
    def parse(cls, text: str) -> "Shortcut":
        """'Ctrl+Alt+G' -> Shortcut; raises ValueError for anything else."""
        *modifier_names, key = [part.strip() for part in text.split("+")]
        by_name = {modifier.value.lower(): modifier for modifier in Modifier}
        try:
            modifiers = frozenset(by_name[name.lower()] for name in modifier_names)
        except KeyError as error:
            raise ValueError(f"Unknown modifier in {text!r}") from error
        return cls(modifiers, key.upper())

    def __str__(self) -> str:
        names = [modifier.value for modifier in _MODIFIER_ORDER if modifier in self.modifiers]
        return "+".join([*names, self.key])


DEFAULT_EMERGENCY_SHORTCUT = Shortcut(frozenset({Modifier.CTRL, Modifier.ALT}), "G")
