"""Common page behavior: header, page-scoped timers and show/hide hooks."""

import tkinter
from collections.abc import Callable

import customtkinter as ctk

from jestkontrol.application.observable import Unsubscribe
from jestkontrol.ui.context import UiContext

PAGE_PADDING = 28


class Page(ctk.CTkFrame):
    def __init__(self, master, ctx: UiContext) -> None:
        super().__init__(master, fg_color="transparent")
        self.ctx = ctx
        self._jobs: dict[str, str] = {}  # one pending after() job per name
        self._subscriptions: list[Unsubscribe] = []
        self.grid_columnconfigure(0, weight=1)

    def header(self, title: str, subtitle: str) -> tuple[ctk.CTkFrame, ctk.CTkLabel]:
        """Title block on the left of row 0; the returned frame's column 1 is free for actions."""
        c = self.ctx.colors
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=0, column=0, sticky="ew", padx=PAGE_PADDING, pady=(PAGE_PADDING - 4, 16))
        row.grid_columnconfigure(0, weight=1)
        block = ctk.CTkFrame(row, fg_color="transparent")
        block.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            block, text=title, anchor="w", font=self.ctx.theme.font("page_title"), text_color=c.text
        ).pack(anchor="w")
        subtitle_label = ctk.CTkLabel(
            block, text=subtitle, anchor="w", font=self.ctx.theme.font("body"), text_color=c.text_2
        )
        subtitle_label.pack(anchor="w")
        return row, subtitle_label

    def listen(self, unsubscribe: Unsubscribe) -> None:
        """Keeps a subscription for the page's lifetime; it is removed when the page is destroyed."""
        self._subscriptions.append(unsubscribe)

    def on_ui_thread(self, action: Callable[[], None]) -> Callable[..., None]:
        """A callback that may fire on any thread; it runs ``action`` on the UI thread if the page still exists."""
        return lambda *_: self.ctx.dispatcher.post(self._if_alive, action)

    def _if_alive(self, action: Callable[[], None]) -> None:
        if self.winfo_exists():
            action()

    def every(self, milliseconds: int, action: Callable[[], None]) -> None:
        """Runs ``action`` repeatedly until the page is destroyed."""

        def tick() -> None:
            action()
            self.schedule(action.__name__, milliseconds, tick)

        self.schedule(action.__name__, milliseconds, tick)

    def schedule(self, name: str, milliseconds: int, action: Callable[[], None]) -> None:
        """Runs ``action`` once after a delay; a newer job with the same name replaces the pending one."""
        try:
            self._jobs[name] = self.after(milliseconds, action)
        except tkinter.TclError:
            pass

    def destroy(self) -> None:
        for unsubscribe in self._subscriptions:
            unsubscribe()
        self._subscriptions.clear()
        for job in self._jobs.values():
            try:
                self.after_cancel(job)
            except tkinter.TclError:
                pass
        self._jobs.clear()
        super().destroy()
