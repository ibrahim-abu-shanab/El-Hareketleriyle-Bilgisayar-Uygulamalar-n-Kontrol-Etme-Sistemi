import logging

from jestkontrol.application.action_dispatcher import ActionDispatcher
from jestkontrol.application.actions import build_action_dispatcher
from jestkontrol.application.system_controller import SystemController
from jestkontrol.domain.gestures import (
    Clicked,
    CursorMoved,
    DragEnded,
    DragStarted,
    GestureEvent,
    MouseButton,
    PauseToggled,
    Scrolled,
    VolumeSet,
)
from jestkontrol.domain.landmarks import Point
from jestkontrol.domain.modes import SystemState
from tests.fakes import FakeMouse, FakeScreen, FakeVolume


def build(controller=None):
    mouse, volume = FakeMouse(), FakeVolume()
    controller = controller or SystemController()
    dispatcher = build_action_dispatcher(mouse, FakeScreen(1920, 1080), volume, controller)
    return dispatcher, mouse, volume, controller


def test_cursor_position_is_scaled_to_screen_pixels():
    dispatcher, mouse, *_ = build()

    dispatcher.dispatch([CursorMoved(Point(0.0, 0.0)), CursorMoved(Point(1.0, 1.0))])

    assert mouse.calls == [("move_to", 0, 0), ("move_to", 1919, 1079)]


def test_click_drag_and_scroll_reach_the_mouse():
    dispatcher, mouse, *_ = build()

    dispatcher.dispatch(
        [Clicked(MouseButton.RIGHT), DragStarted(), DragEnded(), Scrolled(-3)]
    )

    assert mouse.calls == [
        ("click", MouseButton.RIGHT),
        ("press", MouseButton.LEFT),
        ("release", MouseButton.LEFT),
        ("scroll", -3),
    ]


def test_volume_event_sets_system_volume():
    dispatcher, _, volume, _ = build()

    dispatcher.dispatch([VolumeSet(0.4)])

    assert volume.levels == [0.4]


def test_pause_event_toggles_the_system_state():
    controller = SystemController()
    controller.start()
    dispatcher, *_ = build(controller)

    dispatcher.dispatch([PauseToggled()])
    assert controller.state is SystemState.PAUSED
    dispatcher.dispatch([PauseToggled()])
    assert controller.state is SystemState.ACTIVE


def test_unregistered_event_is_logged_and_skipped(caplog):
    class Unknown(GestureEvent):
        pass

    dispatcher = ActionDispatcher()
    seen = []
    dispatcher.register(Clicked, seen.append)

    with caplog.at_level(logging.WARNING):
        dispatcher.dispatch([Unknown(), Clicked(MouseButton.LEFT)])

    assert seen == [Clicked(MouseButton.LEFT)]
    assert "Unknown" in caplog.text
