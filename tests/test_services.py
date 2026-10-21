import time

from jestkontrol.application.services import Adapters, create_services
from jestkontrol.domain.appearance import Language
from jestkontrol.domain.modes import SystemState
from jestkontrol.domain.settings import Settings
from tests.fakes import (
    FakeClock,
    FakeFrameSource,
    FakeHotkey,
    FakeMouse,
    FakeScreen,
    FakeTracker,
    FakeVolume,
)
from tests.hands import open_hand
from tests.test_diagnostics import MemoryRepository, RecordingExporter
from tests.test_metrics_and_settings_store import InMemoryRepository


class OneCamera:
    def available_indices(self, keep=None):
        return [0]


def build(source=None, hands=None, settings=None):
    adapters = Adapters(
        clock=FakeClock(),
        tracker=FakeTracker(hands),
        mouse=FakeMouse(),
        screen=FakeScreen(),
        volume=FakeVolume(),
        hotkey=FakeHotkey(),
        cameras=OneCamera(),
        settings_repository=InMemoryRepository(settings),
        diagnostics_repository=MemoryRepository(),
        exporter=RecordingExporter(),
    )
    services = create_services(adapters, lambda _: source or FakeFrameSource(frame_count=5))
    return services, adapters


def test_translator_follows_the_language_setting():
    services, _ = build(settings=Settings(language=Language.ENGLISH))
    assert services.translator.language is Language.ENGLISH

    services.settings.change(language=Language.TURKISH)

    assert services.translator.language is Language.TURKISH


def test_running_the_pipeline_feeds_monitor_event_log_and_meter():
    services, adapters = build(hands=[open_hand()] * 5)
    seen = []
    services.runtime.add_frame_listener(lambda frame, result: seen.append(result))

    services.runtime.start()
    stopped = []
    services.controller.subscribe(lambda s: stopped.append(s.state) if s.state is SystemState.OFF else None)
    for _ in range(200):
        if stopped:
            break
        time.sleep(0.01)

    assert len(seen) == 5
    assert [e.key for e in services.event_log.recent(10)][-1] == "event.started"
    assert services.monitor.snapshot().frame is None  # cleared once the system turned OFF
    assert adapters.mouse.calls  # the cursor moved


def test_diagnostics_are_cancelled_when_the_system_stops():
    services, _ = build()
    services.diagnostics.start_fps_test(10)
    services.runtime.stop()

    assert not services.diagnostics.is_running


def test_hand_presence_is_wired_to_the_pipeline():
    services, adapters = build(source=FakeFrameSource(frame_count=200), hands=[])
    notices = []
    services.presence.subscribe(lambda: notices.append(True))
    clock = adapters.clock
    services.runtime.add_frame_listener(lambda frame, result: clock.advance(0.1))

    services.runtime.start()
    for _ in range(300):
        if notices or services.controller.state is SystemState.OFF:
            break
        time.sleep(0.01)
    services.runtime.stop()

    assert notices


def test_shutdown_releases_the_emergency_shortcut():
    services, adapters = build()
    services.emergency.activate(lambda: None)
    assert str(adapters.hotkey.registered) == "Ctrl+Alt+G"

    services.shutdown()

    assert adapters.hotkey.registered is None
