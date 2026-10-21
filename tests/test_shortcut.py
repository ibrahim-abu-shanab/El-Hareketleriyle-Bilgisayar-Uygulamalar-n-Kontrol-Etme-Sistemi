import pytest

from jestkontrol.domain.shortcut import DEFAULT_EMERGENCY_SHORTCUT, Modifier, Shortcut


def test_parse_and_format_round_trip_in_canonical_order():
    shortcut = Shortcut.parse("shift+alt+ctrl+k")

    assert shortcut.modifiers == {Modifier.CTRL, Modifier.ALT, Modifier.SHIFT}
    assert str(shortcut) == "Ctrl+Alt+Shift+K"
    assert Shortcut.parse(str(shortcut)) == shortcut


def test_default_is_ctrl_alt_g():
    assert str(DEFAULT_EMERGENCY_SHORTCUT) == "Ctrl+Alt+G"


@pytest.mark.parametrize("text", ["Ctrl+Alt+F12", "Alt+1", "Ctrl+F5"])
def test_valid_shortcuts(text):
    assert str(Shortcut.parse(text)) == text


@pytest.mark.parametrize(
    "text",
    [
        "G",  # no modifier
        "Shift+G",  # Shift alone would steal normal typing
        "Ctrl+Alt+Space",  # unsupported key
        "Ctrl+Alt+F13",
        "Hyper+G",  # unknown modifier
        "Ctrl+Alt+",
    ],
)
def test_invalid_shortcuts_are_rejected(text):
    with pytest.raises(ValueError):
        Shortcut.parse(text)
