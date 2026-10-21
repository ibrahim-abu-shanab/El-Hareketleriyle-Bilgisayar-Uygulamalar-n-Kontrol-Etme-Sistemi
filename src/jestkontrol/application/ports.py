"""Interfaces the application layer needs from the outside world (implemented in infrastructure)."""

from collections.abc import Callable
from typing import Any, Protocol

from jestkontrol.domain.gestures import MouseButton
from jestkontrol.domain.landmarks import HandFrame
from jestkontrol.domain.settings import Settings
from jestkontrol.domain.shortcut import Shortcut

type Frame = Any  # opaque image handed from a FrameSource to a HandTracker


class CameraError(Exception):
    """The camera cannot be opened or stopped delivering frames."""


class Clock(Protocol):
    def now(self) -> float:
        """Monotonic time in seconds."""


class FrameSource(Protocol):
    def open(self) -> None: ...

    def read(self) -> Frame:
        """Return the next frame; raise CameraError if the camera is lost."""

    def close(self) -> None: ...


class HandTracker(Protocol):
    def detect(self, frame: Frame) -> HandFrame | None:
        """Return the tracked hand, or None when no hand is visible.

        Handedness is reported as seen in a mirrored (selfie) image, MediaPipe's convention.
        """

    def close(self) -> None: ...


class ScreenInfo(Protocol):
    def size(self) -> tuple[int, int]:
        """Screen size in pixels (width, height)."""


class MouseController(Protocol):
    def move_to(self, x: int, y: int) -> None: ...

    def click(self, button: MouseButton) -> None: ...

    def press(self, button: MouseButton) -> None: ...

    def release(self, button: MouseButton) -> None: ...

    def scroll(self, notches: int) -> None: ...


class VolumeController(Protocol):
    def set_level(self, level: float) -> None:
        """Set the master volume, level in [0, 1]."""


class SettingsProvider(Protocol):
    @property
    def current(self) -> Settings: ...


class SettingsRepository(Protocol):
    def load(self) -> Settings: ...

    def save(self, settings: Settings) -> None: ...


class CameraCatalog(Protocol):
    def available_indices(self, keep: int | None = None) -> list[int]:
        """Indices of cameras that can be opened; ``keep`` is always included."""


class HotkeyListener(Protocol):
    def start(self, shortcut: Shortcut, on_pressed: Callable[[], None]) -> None:
        """Registers a system-wide shortcut; raises OSError if another application owns it."""

    def stop(self) -> None:
        """Unregisters the shortcut; a no-op when nothing is registered."""
