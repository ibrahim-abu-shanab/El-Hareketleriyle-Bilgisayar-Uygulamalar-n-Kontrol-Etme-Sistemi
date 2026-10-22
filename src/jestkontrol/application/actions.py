"""Handlers that turn gesture events into operating-system actions, plus the default wiring."""

from jestkontrol.application.action_dispatcher import ActionDispatcher
from jestkontrol.application.ports import MouseController, ScreenInfo, VolumeController
from jestkontrol.application.system_controller import SystemController
from jestkontrol.domain.gestures import (
    Clicked,
    CursorMoved,
    DragEnded,
    DragStarted,
    MouseButton,
    PauseToggled,
    Scrolled,
    VolumeSet,
)


class MouseActions:
    def __init__(self, mouse: MouseController, screen: ScreenInfo) -> None:
        self._mouse = mouse
        self._screen = screen

    def on_cursor_moved(self, event: CursorMoved) -> None:
        width, height = self._screen.size()
        self._mouse.move_to(
            round(event.position.x * (width - 1)),
            round(event.position.y * (height - 1)),
        )

    def on_clicked(self, event: Clicked) -> None:
        self._mouse.click(event.button)

    def on_drag_started(self, _: DragStarted) -> None:
        self._mouse.press(MouseButton.LEFT)

    def on_drag_ended(self, _: DragEnded) -> None:
        self._mouse.release(MouseButton.LEFT)

    def on_scrolled(self, event: Scrolled) -> None:
        self._mouse.scroll(event.notches)


class VolumeActions:
    def __init__(self, volume: VolumeController) -> None:
        self._volume = volume

    def on_volume_set(self, event: VolumeSet) -> None:
        self._volume.set_level(event.level)


class PauseActions:
    def __init__(self, controller: SystemController) -> None:
        self._controller = controller

    def on_pause_toggled(self, _: PauseToggled) -> None:
        self._controller.toggle_pause()


def build_action_dispatcher(
    mouse: MouseController,
    screen: ScreenInfo,
    volume: VolumeController,
    controller: SystemController,
) -> ActionDispatcher:
    mouse_actions = MouseActions(mouse, screen)
    dispatcher = ActionDispatcher()
    dispatcher.register(CursorMoved, mouse_actions.on_cursor_moved)
    dispatcher.register(Clicked, mouse_actions.on_clicked)
    dispatcher.register(DragStarted, mouse_actions.on_drag_started)
    dispatcher.register(DragEnded, mouse_actions.on_drag_ended)
    dispatcher.register(Scrolled, mouse_actions.on_scrolled)
    dispatcher.register(VolumeSet, VolumeActions(volume).on_volume_set)
    dispatcher.register(PauseToggled, PauseActions(controller).on_pause_toggled)
    return dispatcher
