"""The object graph of the running application, assembled from port implementations."""

from collections.abc import Callable
from dataclasses import dataclass

from jestkontrol.application.actions import build_action_dispatcher
from jestkontrol.application.camera_selection import CameraSelection
from jestkontrol.application.diagnostics.history import (
    DiagnosticsHistory,
    DiagnosticsRepository,
    ResultsExporter,
)
from jestkontrol.application.diagnostics.runner import DiagnosticsRunner
from jestkontrol.application.emergency_shortcut import EmergencyShortcut
from jestkontrol.application.event_log import EventLog, EventRecorder
from jestkontrol.application.frame_processor import FrameProcessor
from jestkontrol.application.gesture_engine import GestureEngine
from jestkontrol.application.hand_presence import HandPresenceMonitor
from jestkontrol.application.i18n.translator import Translator
from jestkontrol.application.live_monitor import LiveMonitor
from jestkontrol.application.metrics import PerformanceMeter
from jestkontrol.application.ports import (
    CameraCatalog,
    Clock,
    FrameSource,
    HandTracker,
    HotkeyListener,
    MouseController,
    ScreenInfo,
    SettingsProvider,
    SettingsRepository,
    VolumeController,
)
from jestkontrol.application.recognizers.registry import create_default_recognizers
from jestkontrol.application.runtime import GestureRuntime
from jestkontrol.application.settings_store import SettingsStore
from jestkontrol.application.system_controller import SystemController
from jestkontrol.domain.modes import SystemState


@dataclass(frozen=True)
class Adapters:
    """The infrastructure implementations of every port (chosen by the composition root)."""

    clock: Clock
    tracker: HandTracker
    mouse: MouseController
    screen: ScreenInfo
    volume: VolumeController
    hotkey: HotkeyListener
    cameras: CameraCatalog
    settings_repository: SettingsRepository
    diagnostics_repository: DiagnosticsRepository
    exporter: ResultsExporter


@dataclass
class AppServices:
    runtime: GestureRuntime
    controller: SystemController
    settings: SettingsStore
    translator: Translator
    meter: PerformanceMeter
    monitor: LiveMonitor
    presence: HandPresenceMonitor
    event_log: EventLog
    diagnostics: DiagnosticsRunner
    history: DiagnosticsHistory
    camera_selection: CameraSelection
    clock: Clock
    emergency: EmergencyShortcut
    tracker: HandTracker

    def shutdown(self) -> None:
        self.runtime.stop()
        self.emergency.deactivate()
        self.tracker.close()


def create_services(
    adapters: Adapters, source_factory: Callable[[SettingsProvider, CameraSelection], FrameSource]
) -> AppServices:
    """``source_factory(settings, camera_selection)`` builds the FrameSource, which reads live camera settings."""
    settings = SettingsStore(adapters.settings_repository)
    translator = Translator(settings.current.language)
    settings.subscribe(lambda updated: translator.set_language(updated.language))

    controller = SystemController()
    dispatcher = build_action_dispatcher(
        adapters.mouse, adapters.screen, adapters.volume, controller
    )
    processor = FrameProcessor(
        adapters.tracker,
        GestureEngine(create_default_recognizers()),
        dispatcher,
        controller,
        settings,
        adapters.clock,
    )
    meter = PerformanceMeter()
    camera_selection = CameraSelection(adapters.cameras, settings)
    runtime = GestureRuntime(
        source_factory(settings, camera_selection), processor, controller, meter, adapters.clock
    )

    history = DiagnosticsHistory(adapters.diagnostics_repository, adapters.exporter)
    diagnostics = DiagnosticsRunner(runtime, controller, settings, history, adapters.clock)
    monitor = LiveMonitor(adapters.clock)
    presence = HandPresenceMonitor(adapters.clock, controller)
    event_log = EventLog()
    recorder = EventRecorder(event_log)

    runtime.add_frame_listener(monitor.on_frame)
    runtime.add_frame_listener(presence.on_frame)
    runtime.add_frame_listener(recorder.on_frame)
    runtime.add_frame_listener(diagnostics.on_frame)
    controller.subscribe(recorder.on_status)
    controller.subscribe(lambda status: _forget_when_off(status.state, monitor, diagnostics))

    return AppServices(
        runtime,
        controller,
        settings,
        translator,
        meter,
        monitor,
        presence,
        event_log,
        diagnostics,
        history,
        camera_selection,
        adapters.clock,
        EmergencyShortcut(adapters.hotkey, settings),
        adapters.tracker,
    )


def _forget_when_off(state: SystemState, monitor: LiveMonitor, diagnostics: DiagnosticsRunner) -> None:
    if state is SystemState.OFF:
        monitor.clear()
        diagnostics.cancel()
