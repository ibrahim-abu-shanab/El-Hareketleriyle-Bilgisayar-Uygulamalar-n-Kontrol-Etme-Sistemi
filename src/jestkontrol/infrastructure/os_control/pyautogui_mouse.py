"""Mouse and screen access through PyAutoGUI."""

import pyautogui

from jestkontrol.domain.gestures import MouseButton

# Real-time control: no artificial delay after calls, and reaching a screen corner must not abort
# (the global emergency hotkey is the safety stop instead of PyAutoGUI's fail-safe).
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False


class PyAutoGuiMouse:
    def move_to(self, x: int, y: int) -> None:
        pyautogui.moveTo(x, y, _pause=False)

    def click(self, button: MouseButton) -> None:
        pyautogui.click(button=button.value, _pause=False)

    def press(self, button: MouseButton) -> None:
        pyautogui.mouseDown(button=button.value, _pause=False)

    def release(self, button: MouseButton) -> None:
        pyautogui.mouseUp(button=button.value, _pause=False)

    def scroll(self, notches: int) -> None:
        pyautogui.scroll(notches, _pause=False)


class PyAutoGuiScreen:
    def size(self) -> tuple[int, int]:
        width, height = pyautogui.size()
        return width, height
