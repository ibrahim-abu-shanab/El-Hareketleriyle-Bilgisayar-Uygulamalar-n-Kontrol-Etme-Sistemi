"""Draws the camera preview: frame, active-area corners, hand skeleton, status chips and the idle scene."""

from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

from jestkontrol.application.live_monitor import LiveSnapshot
from jestkontrol.application.system_controller import SystemStatus
from jestkontrol.domain.gestures import GestureType
from jestkontrol.domain.landmarks import LandmarkId
from jestkontrol.domain.modes import SystemState
from jestkontrol.domain.settings import Settings
from jestkontrol.ui.context import UiContext

IDLE_SILHOUETTE = "#0D1628"  # darker than the skeleton-art silhouette token: the idle scene stays quiet
REFERENCE_WIDTH = 640  # coordinates below are designed for a 640 px wide preview and scaled from it
REGULAR_FONT = "segoeui.ttf"
SEMIBOLD_FONT = "seguisb.ttf"

# MediaPipe's hand skeleton: pairs of landmark indices that are joined by a bone.
HAND_BONES: tuple[tuple[int, int], ...] = (
    (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11),
    (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17),
)  # fmt: skip

_HIGHLIGHTED_TIPS: dict[GestureType, tuple[LandmarkId, ...]] = {
    GestureType.MOVE: (LandmarkId.INDEX_TIP,),
    GestureType.LEFT_CLICK: (LandmarkId.THUMB_TIP, LandmarkId.INDEX_TIP),
    GestureType.DRAG: (LandmarkId.THUMB_TIP, LandmarkId.INDEX_TIP),
    GestureType.RIGHT_CLICK: (LandmarkId.THUMB_TIP, LandmarkId.MIDDLE_TIP),
    GestureType.SCROLL: (LandmarkId.INDEX_TIP, LandmarkId.MIDDLE_TIP),
    GestureType.VOLUME: (LandmarkId.THUMB_TIP, LandmarkId.INDEX_TIP),
}


def _hex_to_rgba(color: str, opacity: float = 1.0) -> tuple[int, int, int, int]:
    value = color.lstrip("#")
    red, green, blue = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    return red, green, blue, round(255 * opacity)


@dataclass(frozen=True)
class PreviewContent:
    snapshot: LiveSnapshot
    status: SystemStatus
    settings: Settings


class PreviewRenderer:
    def __init__(self, ctx: UiContext) -> None:
        self._ctx = ctx
        self._viewport = ctx.theme.viewport
        self._fonts: dict[tuple[str, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}

    def render(self, size: tuple[int, int], content: PreviewContent) -> Image.Image:
        width, _ = size
        unit = width / REFERENCE_WIDTH
        frame = content.snapshot.frame
        if content.status.state is SystemState.OFF or frame is None:
            canvas = self._idle_scene(size, unit)
        else:
            canvas = Image.fromarray(frame[:, :, ::-1]).resize(size).convert("RGBA")
        overlay = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        self._draw_active_area(draw, size, unit, content.settings.active_area_margin)
        if content.status.state is not SystemState.OFF:
            self._draw_hand(draw, size, unit, content)
            self._draw_chips(draw, size, unit, content)
        else:
            self._draw_idle_guide(draw, size, unit)
        return Image.alpha_composite(canvas, overlay).convert("RGB")

    # --- scenes ------------------------------------------------------------------------------

    def _idle_scene(self, size: tuple[int, int], unit: float) -> Image.Image:
        canvas = Image.new("RGBA", size, _hex_to_rgba(self._viewport["background"]))
        draw = ImageDraw.Draw(canvas)
        silhouette = _hex_to_rgba(IDLE_SILHOUETTE)

        def box(left: float, top: float, right: float, bottom: float) -> tuple[float, ...]:
            return left * unit, top * unit, right * unit, bottom * unit

        draw.ellipse(box(198, 116, 326, 276), fill=silhouette)
        draw.rectangle(box(226, 262, 298, 318), fill=silhouette)
        draw.pieslice(box(92, 322, 432, 700), 180, 360, fill=silhouette)
        return canvas

    def _draw_idle_guide(self, draw: ImageDraw.ImageDraw, size: tuple[int, int], unit: float) -> None:
        t = self._ctx.t
        shortcut = str(self._ctx.services.emergency.current)
        steps = [t("preview.off.step1"), t("preview.off.step2", shortcut=shortcut), t("preview.off.step3")]
        width, height = size
        title_font, step_font = self._font(SEMIBOLD_FONT, 20 * unit), self._font(REGULAR_FONT, 15 * unit)
        left = width * 0.27
        top = height * 0.60
        draw.text((left, top), t("preview.off.title"), font=title_font, fill=_hex_to_rgba("#F8FAFC"))
        for number, step in enumerate(steps, start=1):
            y = top + (38 + 32 * (number - 1)) * unit
            radius = 11 * unit
            draw.ellipse((left, y - radius + 8 * unit, left + 2 * radius, y + radius + 8 * unit), fill=_hex_to_rgba("#1C3F53"))
            draw.text((left + radius, y + 8 * unit), str(number), font=step_font, fill=_hex_to_rgba("#67E8F9"), anchor="mm")
            draw.text((left + 2 * radius + 12 * unit, y + 8 * unit), step, font=step_font, fill=_hex_to_rgba("#CBD5E1"), anchor="lm")

    # --- overlays ----------------------------------------------------------------------------

    def _draw_active_area(
        self, draw: ImageDraw.ImageDraw, size: tuple[int, int], unit: float, margin: float
    ) -> None:
        width, height = size
        color = _hex_to_rgba(self._viewport["control_zone"], self._viewport["control_zone_opacity"])
        arm = 26 * unit
        left, top = max(margin, 0.08) * width, max(margin, 0.08) * height
        right, bottom = width - left, height - top
        line = max(round(2.5 * unit), 2)
        for x, y, dx, dy in ((left, top, 1, 1), (right, top, -1, 1), (left, bottom, 1, -1), (right, bottom, -1, -1)):
            draw.line([(x + dx * arm, y), (x, y), (x, y + dy * arm)], fill=color, width=line, joint="curve")
        label = self._ctx.t("preview.active_area")
        draw.text((left + 10 * unit, top + 8 * unit), label, font=self._font(REGULAR_FONT, 13 * unit), fill=_hex_to_rgba("#CBD5E1", 0.6))

    def _draw_hand(self, draw: ImageDraw.ImageDraw, size: tuple[int, int], unit: float, content: PreviewContent) -> None:
        hand = content.snapshot.hand
        if hand is None or not content.settings.show_skeleton:
            return
        width, height = size
        paused = content.status.state is SystemState.PAUSED
        bone_color = _hex_to_rgba(self._viewport["skeleton_paused" if paused else "skeleton"])
        points = [(p.x * width, p.y * height) for p in hand.landmarks]
        for start, end in HAND_BONES:
            draw.line([points[start], points[end]], fill=bone_color, width=max(round(2.5 * unit), 2))
        radius = 3.6 * unit
        for x, y in points:
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=_hex_to_rgba(self._viewport["joint_fill"]), outline=bone_color, width=max(round(1.5 * unit), 1))
        if not paused:
            self._draw_highlight(draw, points, unit, content.snapshot.gesture)

    def _draw_highlight(self, draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], unit: float, gesture: GestureType | None) -> None:
        color = _hex_to_rgba(self._viewport["highlight"])
        for tip in _HIGHLIGHTED_TIPS.get(gesture, ()):
            x, y = points[tip]
            ring, dot = 13 * unit, 6.5 * unit
            draw.ellipse((x - ring, y - ring, x + ring, y + ring), outline=_hex_to_rgba(self._viewport["highlight"], 0.7), width=max(round(2 * unit), 1))
            draw.ellipse((x - dot, y - dot, x + dot, y + dot), fill=color)

    def _draw_chips(self, draw: ImageDraw.ImageDraw, size: tuple[int, int], unit: float, content: PreviewContent) -> None:
        t = self._ctx.t
        width, height = size
        paused = content.status.state is SystemState.PAUSED
        mode_text = t("state.paused") if paused else t(f"preview.chip.{content.status.mode.value}")
        self._chip(draw, (14 * unit, 14 * unit), mode_text, unit)
        gesture = content.snapshot.gesture
        if gesture is not None and not paused:
            text = t(f"gesture.{gesture.value}.short")
            self._chip(draw, (14 * unit, height - 14 * unit), text, unit, anchor_bottom=True, dot=True)

    def _chip(self, draw: ImageDraw.ImageDraw, origin: tuple[float, float], text: str, unit: float, anchor_bottom: bool = False, dot: bool = False) -> None:
        font = self._font(SEMIBOLD_FONT, 15 * unit)
        pad_x, pad_y = 14 * unit, 8 * unit
        dot_space = 22 * unit if dot else 0
        left, bottom_or_top = origin
        text_width = draw.textlength(text, font=font)
        box_width = text_width + 2 * pad_x + dot_space
        box_height = 30 * unit + pad_y / 2
        top = bottom_or_top - box_height if anchor_bottom else bottom_or_top
        draw.rounded_rectangle((left, top, left + box_width, top + box_height), radius=box_height / 2, fill=_hex_to_rgba("#0F172A", 0.84), outline=_hex_to_rgba("#334155"), width=1)
        if dot:
            cx, cy = left + pad_x + 6 * unit, top + box_height / 2
            draw.ellipse((cx - 6 * unit, cy - 6 * unit, cx + 6 * unit, cy + 6 * unit), fill=_hex_to_rgba(self._viewport["highlight"]))
        draw.text((left + pad_x + dot_space, top + box_height / 2), text, font=font, fill=_hex_to_rgba(self._viewport["chip_text"]), anchor="lm")

    def _font(self, file: str, size: float) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        key = (file, round(size))
        if key not in self._fonts:
            try:
                self._fonts[key] = ImageFont.truetype(file, round(size))
            except OSError:
                self._fonts[key] = ImageFont.load_default()
        return self._fonts[key]


def round_corners(image: Image.Image, radius: int, background: str) -> Image.Image:
    """Rounds the image corners, filling the cut-off areas with ``background`` (a #RRGGBB color)."""
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *image.size), radius=radius, fill=255)
    canvas = Image.new("RGB", image.size, background)
    canvas.paste(image, mask=mask)
    return canvas
