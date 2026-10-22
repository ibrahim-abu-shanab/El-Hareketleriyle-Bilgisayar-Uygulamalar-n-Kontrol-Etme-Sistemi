import pytest

from jestkontrol.domain.shortcut import Shortcut
from jestkontrol.infrastructure.hotkey.win_hotkey_listener import (
    MOD_ALT,
    MOD_CONTROL,
    MOD_NOREPEAT,
    MOD_SHIFT,
    VK_F1,
    to_win32,
)


@pytest.mark.parametrize(
    ("text", "flags", "virtual_key"),
    [
        ("Ctrl+Alt+G", MOD_CONTROL | MOD_ALT, ord("G")),
        ("Alt+Shift+7", MOD_ALT | MOD_SHIFT, ord("7")),
        ("Ctrl+F5", MOD_CONTROL, VK_F1 + 4),
        ("Ctrl+Alt+F12", MOD_CONTROL | MOD_ALT, VK_F1 + 11),
    ],
)
def test_shortcut_to_register_hotkey_arguments(text, flags, virtual_key):
    assert to_win32(Shortcut.parse(text)) == (flags | MOD_NOREPEAT, virtual_key)
