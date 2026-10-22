import pytest

from jestkontrol.ui.widgets.shortcut_dialog import shortcut_from_key

SHIFT, CTRL, ALT = 0x0001, 0x0004, 0x20000


@pytest.mark.parametrize(
    ("keycode", "state", "expected"),
    [
        (ord("G"), CTRL | ALT, "Ctrl+Alt+G"),
        (ord("7"), ALT | SHIFT, "Alt+Shift+7"),
        (0x74, CTRL, "Ctrl+F5"),
        (0x7B, CTRL | ALT, "Ctrl+Alt+F12"),
    ],
)
def test_key_presses_become_shortcuts(keycode, state, expected):
    assert str(shortcut_from_key(keycode, state)) == expected


@pytest.mark.parametrize(
    ("keycode", "state"),
    [
        (0x11, CTRL),  # Ctrl alone
        (0x12, CTRL | ALT),  # Alt key itself
        (ord("G"), 0),  # no modifier
        (ord("G"), SHIFT),  # Shift is not enough
        (0x20, CTRL | ALT),  # space is not supported
    ],
)
def test_incomplete_or_unsupported_presses_give_nothing(keycode, state):
    assert shortcut_from_key(keycode, state) is None
