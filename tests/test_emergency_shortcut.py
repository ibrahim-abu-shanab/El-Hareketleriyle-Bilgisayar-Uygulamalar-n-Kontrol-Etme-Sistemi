import pytest

from jestkontrol.application.emergency_shortcut import EmergencyShortcut
from jestkontrol.application.settings_store import SettingsStore
from jestkontrol.domain.settings import Settings
from jestkontrol.domain.shortcut import Shortcut
from tests.fakes import FakeHotkey
from tests.test_metrics_and_settings_store import InMemoryRepository

CTRL_ALT_G = Shortcut.parse("Ctrl+Alt+G")
CTRL_ALT_H = Shortcut.parse("Ctrl+Alt+H")


def make(settings=None, taken=()):
    hotkey = FakeHotkey(taken=set(taken))
    store = SettingsStore(InMemoryRepository(settings))
    return EmergencyShortcut(hotkey, store), hotkey, store


def test_activate_registers_the_saved_shortcut():
    emergency, hotkey, _ = make(Settings(emergency_shortcut=CTRL_ALT_H))

    emergency.activate(lambda: None)

    assert hotkey.registered == CTRL_ALT_H


def test_activate_fails_when_another_app_owns_the_shortcut():
    emergency, hotkey, _ = make(taken={CTRL_ALT_G})

    with pytest.raises(OSError):
        emergency.activate(lambda: None)
    assert hotkey.registered is None


def test_change_registers_and_saves_the_new_shortcut():
    emergency, hotkey, store = make()
    pressed = []
    emergency.activate(lambda: pressed.append(True))

    emergency.change(CTRL_ALT_H)
    hotkey.press()

    assert hotkey.registered == CTRL_ALT_H
    assert store.current.emergency_shortcut == CTRL_ALT_H
    assert pressed == [True]


def test_failed_change_keeps_the_previous_shortcut_active_and_unsaved():
    emergency, hotkey, store = make(taken={CTRL_ALT_H})
    emergency.activate(lambda: None)

    with pytest.raises(OSError):
        emergency.change(CTRL_ALT_H)

    assert hotkey.registered == CTRL_ALT_G
    assert store.current.emergency_shortcut == CTRL_ALT_G


def test_suspend_and_resume():
    emergency, hotkey, _ = make()
    emergency.activate(lambda: None)

    emergency.suspend()
    assert hotkey.registered is None
    emergency.resume()
    assert hotkey.registered == CTRL_ALT_G


def test_change_before_activation_only_saves():
    emergency, hotkey, store = make()

    emergency.change(CTRL_ALT_H)

    assert store.current.emergency_shortcut == CTRL_ALT_H
    assert hotkey.registered is None


def test_deactivate_releases_and_resume_does_nothing_afterwards():
    emergency, hotkey, _ = make()
    emergency.activate(lambda: None)

    emergency.deactivate()
    emergency.resume()

    assert hotkey.registered is None
