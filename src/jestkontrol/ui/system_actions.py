"""User-facing system controls (start, stop, pause) shared by the dashboard, mini window and hotkey."""

import threading
from collections.abc import Callable

from jestkontrol.application.ports import CameraError
from jestkontrol.domain.modes import SystemState
from jestkontrol.ui.context import UiContext
from jestkontrol.ui.widgets.feedback import DialogButton


class SystemActions:
    def __init__(self, ctx: UiContext) -> None:
        self._ctx = ctx
        self._services = ctx.services
        self._services.runtime.add_error_listener(self._on_runtime_error)

    def start(self) -> None:
        """Starts the camera pipeline without blocking the UI; a failure opens the camera dialog."""
        self.run_with_camera(self._services.runtime.start)

    def stop(self) -> None:
        threading.Thread(target=self._services.runtime.stop, name="system-stop", daemon=True).start()

    def run_with_camera(self, task: Callable[[], None]) -> None:
        """Runs a task that needs the camera off the UI thread; a camera failure opens the dialog."""

        def work() -> None:
            try:
                task()
            except CameraError:
                self._ctx.dispatcher.post(self._show_camera_failed)

        threading.Thread(target=work, name="camera-task", daemon=True).start()

    def toggle_pause(self) -> None:
        self._services.controller.toggle_pause()

    def toggle_running(self) -> None:
        if self._services.controller.state is SystemState.OFF:
            self.start()
        else:
            self.stop()

    def restart_if_running(self) -> None:
        """Applies camera settings that are only read when the camera opens."""
        if self._services.controller.state is SystemState.OFF:
            return

        def restart() -> None:
            self._services.runtime.stop()
            self._services.runtime.start()
            self._ctx.dispatcher.post(lambda: self._ctx.toast(self._ctx.t("toast.restart_for_camera"), tone="info"))

        self.run_with_camera(restart)

    def _on_runtime_error(self, error: Exception) -> None:
        if isinstance(error, CameraError):
            self._ctx.dispatcher.post(self._ctx.toast, self._ctx.t("toast.camera_lost"), tone="danger")

    def _show_camera_failed(self) -> None:
        camera = self._services.camera_selection.label() or self._ctx.t("camera.generic")
        self._ctx.dialog(
            title=self._ctx.t("dialog.camera_failed.title"),
            text=self._ctx.t("dialog.camera_failed.text", camera=camera),
            buttons=[
                DialogButton(self._ctx.t("action.change_camera"), "secondary", lambda: self._ctx.navigate("settings")),
                DialogButton(self._ctx.t("action.retry"), "primary", self.start),
            ],
            icon="error",
            tone="danger",
        )
