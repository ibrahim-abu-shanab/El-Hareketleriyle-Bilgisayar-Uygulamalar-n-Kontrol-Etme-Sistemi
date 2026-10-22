"""Records a new emergency shortcut from the keyboard (the design's "Değiştir" button)."""

import customtkinter as ctk

from jestkontrol.domain.shortcut import Modifier, Shortcut
from jestkontrol.ui.context import UiContext
from jestkontrol.ui.widgets.controls import make_button
from jestkontrol.ui.widgets.feedback import close_modal, open_modal, show_modal

# Tk on Windows: modifier bits of event.state, and event.keycode is the Windows virtual-key code.
_STATE_BITS = ((Modifier.SHIFT, 0x0001), (Modifier.CTRL, 0x0004), (Modifier.ALT, 0x20000))
_VK_DIGITS = range(0x30, 0x3A)
_VK_LETTERS = range(0x41, 0x5B)
_VK_FUNCTION_KEYS = range(0x70, 0x7C)  # F1..F12


def shortcut_from_key(keycode: int, state: int) -> Shortcut | None:
    """The shortcut a key press forms, or None (modifier only, unsupported key or no Ctrl/Alt).

    Uses the virtual-key code, so layouts where Ctrl+Alt types another character (AltGr) still work.
    """
    if keycode in _VK_DIGITS or keycode in _VK_LETTERS:
        key = chr(keycode)
    elif keycode in _VK_FUNCTION_KEYS:
        key = f"F{keycode - _VK_FUNCTION_KEYS.start + 1}"
    else:
        return None
    modifiers = frozenset(modifier for modifier, bit in _STATE_BITS if state & bit)
    try:
        return Shortcut(modifiers, key)
    except ValueError:
        return None


def show_shortcut_dialog(window, ctx: UiContext) -> None:
    """While open, the current shortcut is released so pressing it does not start or stop the system."""
    c, emergency = ctx.colors, ctx.services.emergency
    dialog, body = open_modal(
        window, ctx, ctx.t("shortcut.dialog.title"), ctx.t("shortcut.dialog.text"), "keyboard", "info"
    )
    captured: list[Shortcut] = []
    preview = ctk.CTkLabel(
        body, text=ctx.t("shortcut.dialog.waiting"), height=48, corner_radius=ctx.theme.radius["tile"],
        fg_color=c.bg, text_color=c.text, font=ctk.CTkFont(family=ctx.theme.mono_family, size=20, weight="bold"),
    )
    preview.grid(row=2, column=1, sticky="ew")
    message = ctk.CTkLabel(body, text="", anchor="w", font=ctx.theme.font("caption"), text_color=c.danger_text)
    message.grid(row=3, column=1, sticky="w", pady=(6, 14))
    buttons = ctk.CTkFrame(body, fg_color="transparent")
    buttons.grid(row=4, column=1, sticky="e")

    def cancel() -> None:
        close_modal(dialog)
        _resume_quietly(ctx)

    def save() -> None:
        try:
            emergency.change(captured[-1])
        except OSError:
            message.configure(text=ctx.t("shortcut.dialog.taken"))
            emergency.suspend()  # keep the old one released while the dialog stays open
            return
        close_modal(dialog)
        ctx.toast(ctx.t("toast.shortcut_saved", shortcut=str(captured[-1])))

    def on_key(event) -> None:
        shortcut = shortcut_from_key(event.keycode, event.state)
        if shortcut is None:
            if event.keycode not in (0x10, 0x11, 0x12):  # a lone Shift/Ctrl/Alt is not an error yet
                message.configure(text=ctx.t("shortcut.dialog.invalid"))
            return
        captured.append(shortcut)
        preview.configure(text=str(shortcut))
        message.configure(text="")
        save_button.configure(state="normal")

    make_button(buttons, ctx, ctx.t("action.cancel"), command=cancel).pack(side="left", padx=(8, 0))
    save_button = make_button(buttons, ctx, ctx.t("action.save"), style="primary", command=save)
    save_button.configure(state="disabled")
    save_button.pack(side="left", padx=(8, 0))

    emergency.suspend()
    dialog.protocol("WM_DELETE_WINDOW", cancel)
    dialog.bind("<KeyPress>", on_key)
    show_modal(window, dialog)
    dialog.after(80, dialog.focus_force)


def _resume_quietly(ctx: UiContext) -> None:
    try:
        ctx.services.emergency.resume()
    except OSError:
        ctx.toast(ctx.t("toast.hotkey_unavailable"), tone="warning")
