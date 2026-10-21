import pytest

from jestkontrol.application.metrics import PerformanceMeter
from jestkontrol.application.settings_store import SettingsStore
from jestkontrol.domain.settings import Settings


class InMemoryRepository:
    def __init__(self, stored: Settings | None = None) -> None:
        self.stored = stored or Settings()
        self.saves = 0

    def load(self) -> Settings:
        return self.stored

    def save(self, settings: Settings) -> None:
        self.stored = settings
        self.saves += 1


def test_meter_reports_zero_before_enough_samples():
    snapshot = PerformanceMeter().snapshot()

    assert (snapshot.fps, snapshot.latency_ms) == (0.0, 0.0)


def test_meter_computes_fps_and_mean_latency():
    meter = PerformanceMeter()
    for frame in range(6):  # a frame every 40 ms, each taking 20 ms to process
        started = frame * 0.04
        meter.record(started, started + 0.02)

    snapshot = meter.snapshot()

    assert snapshot.fps == pytest.approx(25.0)
    assert snapshot.latency_ms == pytest.approx(20.0)


def test_meter_only_keeps_the_rolling_window():
    meter = PerformanceMeter(window=3)
    for finished in (0.0, 10.0, 10.1, 10.2):  # the slow first frame falls out of the window
        meter.record(finished - 0.01, finished)

    assert meter.snapshot().fps == pytest.approx(10.0)


def test_meter_reset_clears_history():
    meter = PerformanceMeter()
    meter.record(0.0, 0.1)
    meter.record(0.1, 0.2)

    meter.reset()

    assert meter.snapshot().fps == 0.0


def test_store_loads_persisted_settings():
    stored = Settings(sensitivity=1.5)

    assert SettingsStore(InMemoryRepository(stored)).current == stored


def test_store_change_applies_persists_and_notifies():
    repository = InMemoryRepository()
    store = SettingsStore(repository)
    seen = []
    store.subscribe(seen.append)

    store.change(smoothing_percent=20)

    assert store.current.smoothing_percent == 20
    assert repository.stored.smoothing_percent == 20
    assert seen == [store.current]


def test_store_change_is_validated():
    store = SettingsStore(InMemoryRepository())

    store.change(sensitivity=50)

    assert store.current.sensitivity == 2.0


def test_store_reset_to_defaults():
    store = SettingsStore(InMemoryRepository(Settings(sensitivity=1.9)))

    store.reset_to_defaults()

    assert store.current == Settings()
