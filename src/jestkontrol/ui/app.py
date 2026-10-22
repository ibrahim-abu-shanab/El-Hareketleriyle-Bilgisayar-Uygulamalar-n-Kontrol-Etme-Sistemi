"""Graphical entry point."""

import gc
import tkinter

from jestkontrol.application.services import AppServices
from jestkontrol.ui.main_window import MainWindow

YOUNG_COLLECTION_INTERVAL_MS = 1000
FULL_COLLECTION_EVERY = 30  # young collections


class UiThreadGarbageCollector:
    """Runs garbage collection on the UI thread only.

    Automatic collection may run on the capture thread; finalizers of Tk images found there must
    call into Tcl, which waits for the UI thread and stalls the camera loop for up to a second.
    """

    def __init__(self, root: tkinter.Misc) -> None:
        self._root = root
        self._ticks = 0
        gc.disable()
        self._root.after(YOUNG_COLLECTION_INTERVAL_MS, self._collect)

    def _collect(self) -> None:
        self._ticks += 1
        gc.collect(2 if self._ticks % FULL_COLLECTION_EVERY == 0 else 1)
        try:
            self._root.after(YOUNG_COLLECTION_INTERVAL_MS, self._collect)
        except tkinter.TclError:
            pass


def run_gui(services: AppServices) -> int:
    window = MainWindow(services)
    UiThreadGarbageCollector(window)
    try:
        window.mainloop()
    finally:
        gc.enable()
    return 0
