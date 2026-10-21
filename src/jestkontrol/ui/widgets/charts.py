"""A small line chart drawn on a tk.Canvas (FPS per second with the target line)."""

import tkinter
from collections.abc import Sequence

from jestkontrol.ui.context import UiContext

PAD_LEFT, PAD_RIGHT, PAD_TOP, PAD_BOTTOM = 38, 18, 12, 26
Y_STEP = 10
X_LABELS = 5


class FpsChart(tkinter.Canvas):
    def __init__(self, master, ctx: UiContext, height: int = 190) -> None:
        super().__init__(master, height=height, bd=0, highlightthickness=0)
        self._ctx = ctx
        self._values: tuple[float, ...] = ()
        self._duration = 30
        self._target = 25.0
        self.bind("<Configure>", lambda _: self._redraw())

    def update_data(self, values: Sequence[float], duration: int, target: float) -> None:
        values = tuple(values)
        if (values, duration, target) == (self._values, self._duration, self._target):
            return
        self._values, self._duration, self._target = values, duration, target
        self._redraw()

    def _redraw(self) -> None:
        theme, colors = self._ctx.theme, self._ctx.colors
        resolve = theme.resolve
        width, height = self.winfo_width(), self.winfo_height()
        if width < 60 or height < 60:
            return
        self.delete("all")
        self.configure(bg=resolve(colors.card))
        top_value = max(40, -(-int(max(self._values, default=0) + 1) // Y_STEP) * Y_STEP)
        left, right, top, bottom = PAD_LEFT, width - PAD_RIGHT, PAD_TOP, height - PAD_BOTTOM
        axis = resolve(colors.text_muted)

        def x_at(second: float) -> float:
            return left + (right - left) * second / max(self._duration, 1)

        def y_at(value: float) -> float:
            return bottom - (bottom - top) * value / top_value

        for value in range(0, top_value + 1, Y_STEP):
            self.create_line(left, y_at(value), right, y_at(value), fill=resolve(colors.border))
            self.create_text(left - 8, y_at(value), text=str(value), fill=axis, anchor="e", font=(theme.font("caption").cget("family"), 9))
        for step in range(X_LABELS + 1):
            second = self._duration * step / X_LABELS
            self.create_text(x_at(second), bottom + 12, text=f"{second:g}", fill=axis, font=(theme.font("caption").cget("family"), 9))
        points = [(x_at(i + 0.5), y_at(v)) for i, v in enumerate(self._values)]
        if len(points) > 1:
            area = [(points[0][0], bottom), *points, (points[-1][0], bottom)]
            self.create_polygon([c for p in area for c in p], fill=resolve(colors.primary_tint), outline="")
            self.create_line([c for p in points for c in p], fill=resolve(colors.primary), width=2, smooth=True)
        # the target line is drawn over the filled area so it stays readable
        self.create_line(left, y_at(self._target), right, y_at(self._target), fill=resolve(colors.text_muted), dash=(5, 4))
        self.create_text(right, y_at(self._target) + 10, text=self._ctx.t("tests.fps.chart_target", value=int(self._target)), fill=resolve(colors.text_2), anchor="e", font=(theme.font("caption").cget("family"), 9))
        if points:
            x, y = points[-1]
            self.create_oval(x - 4, y - 4, x + 4, y + 4, fill=resolve(colors.primary), outline="")
