"""Lifecycle state (OFF / ACTIVE / PAUSED) and operating mode of the system."""

import threading
from collections.abc import Callable
from dataclasses import dataclass, replace

from jestkontrol.application.observable import Listeners, Unsubscribe
from jestkontrol.domain.modes import OperatingMode, SystemState


@dataclass(frozen=True, slots=True)
class SystemStatus:
    state: SystemState
    mode: OperatingMode


class SystemController:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._status = SystemStatus(SystemState.OFF, OperatingMode.MOUSE)
        self._listeners = Listeners()

    @property
    def status(self) -> SystemStatus:
        return self._status

    @property
    def state(self) -> SystemState:
        return self._status.state

    @property
    def mode(self) -> OperatingMode:
        return self._status.mode

    def subscribe(self, listener: Callable[[SystemStatus], None]) -> Unsubscribe:
        return self._listeners.add(listener)

    def start(self) -> None:
        self._move_state({SystemState.OFF}, SystemState.ACTIVE)

    def stop(self) -> None:
        self._move_state({SystemState.ACTIVE, SystemState.PAUSED}, SystemState.OFF)

    def pause(self) -> None:
        self._move_state({SystemState.ACTIVE}, SystemState.PAUSED)

    def resume(self) -> None:
        self._move_state({SystemState.PAUSED}, SystemState.ACTIVE)

    def toggle_pause(self) -> None:
        if self.state is SystemState.ACTIVE:
            self.pause()
        else:
            self.resume()

    def set_mode(self, mode: OperatingMode) -> None:
        self._update(lambda status: replace(status, mode=mode))

    def _move_state(self, allowed_from: set[SystemState], target: SystemState) -> None:
        self._update(
            lambda status: replace(status, state=target) if status.state in allowed_from else status
        )

    def _update(self, change: Callable[[SystemStatus], SystemStatus]) -> None:
        with self._lock:
            previous = self._status
            self._status = change(previous)
            current = self._status
        if current != previous:
            self._listeners.notify(current)
