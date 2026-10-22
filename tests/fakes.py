"""Test doubles for every application port."""

from jestkontrol.application.ports import CameraError
from jestkontrol.domain.gestures import MouseButton
from jestkontrol.domain.landmarks import HandFrame
from jestkontrol.domain.settings import Settings


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def now(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


class FakeMouse:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def move_to(self, x: int, y: int) -> None:
        self.calls.append(("move_to", x, y))

    def click(self, button: MouseButton) -> None:
        self.calls.append(("click", button))

    def press(self, button: MouseButton) -> None:
        self.calls.append(("press", button))

    def release(self, button: MouseButton) -> None:
        self.calls.append(("release", button))

    def scroll(self, notches: int) -> None:
        self.calls.append(("scroll", notches))


class FakeVolume:
    def __init__(self) -> None:
        self.levels: list[float] = []

    def set_level(self, level: float) -> None:
        self.levels.append(level)


class FakeScreen:
    def __init__(self, width: int = 1920, height: int = 1080) -> None:
        self._size = (width, height)

    def size(self) -> tuple[int, int]:
        return self._size


class FakeSettingsProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        self.current = settings or Settings()


class FakeTracker:
    """Returns the queued hands one per frame (None = no hand), then None forever."""

    def __init__(self, hands: list[HandFrame | None] | None = None) -> None:
        self._hands = list(hands or [])
        self.closed = False

    def detect(self, frame) -> HandFrame | None:
        return self._hands.pop(0) if self._hands else None

    def close(self) -> None:
        self.closed = True


class FakeFrameSource:
    """Yields ``frame_count`` frames, then raises CameraError (camera unplugged)."""

    def __init__(self, frame_count: int = 3, fail_on_open: bool = False) -> None:
        self._remaining = frame_count
        self._fail_on_open = fail_on_open
        self.opened = False
        self.closed = False

    def open(self) -> None:
        if self._fail_on_open:
            raise CameraError("cannot open")
        self.opened = True

    def read(self):
        if self._remaining <= 0:
            raise CameraError("camera lost")
        self._remaining -= 1
        return object()

    def close(self) -> None:
        self.closed = True


class FakeHotkey:
    """Registers one shortcut; shortcuts in ``taken`` behave as if another app owns them."""

    def __init__(self, taken: set | None = None) -> None:
        self._taken = taken or set()
        self.registered = None
        self._on_pressed = None

    def start(self, shortcut, on_pressed) -> None:
        if shortcut in self._taken:
            raise OSError("taken")
        self.registered, self._on_pressed = shortcut, on_pressed

    def stop(self) -> None:
        self.registered, self._on_pressed = None, None

    def press(self) -> None:
        self._on_pressed()


class FakeCameraCatalog:
    """Lists ``names`` as cameras 0, 1, 2...; ``calls`` counts how often the system was asked."""

    def __init__(self, names=("HD Webcam",)) -> None:
        self.names = list(names)
        self.calls = 0

    def list_cameras(self):
        from jestkontrol.domain.camera import CameraDevice

        self.calls += 1
        return [CameraDevice(index, name) for index, name in enumerate(self.names)]
