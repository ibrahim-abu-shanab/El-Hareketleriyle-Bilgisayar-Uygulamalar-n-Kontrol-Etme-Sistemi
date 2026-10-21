"""System-wide hotkey through the Win32 RegisterHotKey API."""

import ctypes
import threading
from collections.abc import Callable
from ctypes import wintypes

from jestkontrol.domain.shortcut import Modifier, Shortcut

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
VK_F1 = 0x70
_MODIFIER_FLAGS = {Modifier.CTRL: MOD_CONTROL, Modifier.ALT: MOD_ALT, Modifier.SHIFT: MOD_SHIFT}
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

_HOTKEY_ID = 1
_JOIN_TIMEOUT_S = 2.0

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32


def to_win32(shortcut: Shortcut) -> tuple[int, int]:
    """(modifier flags, virtual-key code) for RegisterHotKey."""
    flags = MOD_NOREPEAT
    for modifier in shortcut.modifiers:
        flags |= _MODIFIER_FLAGS[modifier]
    key = shortcut.key
    virtual_key = VK_F1 + int(key[1:]) - 1 if len(key) > 1 else ord(key)
    return flags, virtual_key


class WinHotkeyListener:
    def __init__(self) -> None:
        self._modifiers = 0
        self._virtual_key = 0
        self._thread: threading.Thread | None = None
        self._thread_id = 0

    def start(self, shortcut: Shortcut, on_pressed: Callable[[], None]) -> None:
        """Raises OSError if another application already owns the hotkey."""
        self.stop()
        self._modifiers, self._virtual_key = to_win32(shortcut)
        registered = threading.Event()
        failed: list[OSError] = []
        self._thread = threading.Thread(
            target=self._message_loop,
            args=(on_pressed, registered, failed),
            name="hotkey-listener",
            daemon=True,
        )
        self._thread.start()
        registered.wait()
        if failed:
            self._thread.join(_JOIN_TIMEOUT_S)
            self._thread = None
            raise failed[0]

    def stop(self) -> None:
        if self._thread is None:
            return
        _user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        self._thread.join(_JOIN_TIMEOUT_S)
        self._thread = None

    def _message_loop(
        self,
        on_pressed: Callable[[], None],
        registered: threading.Event,
        failed: list[OSError],
    ) -> None:
        # RegisterHotKey is bound to the calling thread, which must also pump its messages.
        if not _user32.RegisterHotKey(None, _HOTKEY_ID, self._modifiers, self._virtual_key):
            failed.append(OSError("The emergency hotkey is already used by another application"))
            registered.set()
            return
        self._thread_id = _kernel32.GetCurrentThreadId()
        registered.set()
        try:
            message = wintypes.MSG()
            while _user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                if message.message == WM_HOTKEY:
                    on_pressed()
        finally:
            _user32.UnregisterHotKey(None, _HOTKEY_ID)
