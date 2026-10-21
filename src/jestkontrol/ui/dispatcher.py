"""Runs callables on the Tk main thread; safe to call from any thread."""

import logging
import queue
import tkinter
from collections.abc import Callable

logger = logging.getLogger(__name__)

POLL_INTERVAL_MS = 30


class UiDispatcher:
    def __init__(self, root: tkinter.Misc) -> None:
        self._root = root
        self._pending: queue.SimpleQueue[Callable[[], None]] = queue.SimpleQueue()
        self._poll()

    def post(self, action: Callable[..., None], *args: object, **kwargs: object) -> None:
        self._pending.put(lambda: action(*args, **kwargs))

    def _poll(self) -> None:
        while not self._pending.empty():
            try:
                self._pending.get_nowait()()
            except Exception:  # one failing callback must not stop the UI loop
                logger.exception("UI callback failed")
        try:
            self._root.after(POLL_INTERVAL_MS, self._poll)
        except tkinter.TclError:  # the window was destroyed
            pass
