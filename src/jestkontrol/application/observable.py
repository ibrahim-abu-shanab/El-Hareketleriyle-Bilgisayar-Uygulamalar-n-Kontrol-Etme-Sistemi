"""A thread-safe list of callbacks; adding one returns the function that removes it again."""

import threading
from collections.abc import Callable

Unsubscribe = Callable[[], None]


class Listeners:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._callbacks: list[Callable[..., None]] = []

    def add(self, callback: Callable[..., None]) -> Unsubscribe:
        with self._lock:
            self._callbacks.append(callback)

        def remove() -> None:
            with self._lock:
                if callback in self._callbacks:
                    self._callbacks.remove(callback)

        return remove

    def notify(self, *args: object) -> None:
        with self._lock:
            callbacks = list(self._callbacks)
        for callback in callbacks:
            callback(*args)
