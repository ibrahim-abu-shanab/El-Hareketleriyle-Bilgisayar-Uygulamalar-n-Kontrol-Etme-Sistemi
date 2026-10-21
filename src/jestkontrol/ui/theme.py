"""Design tokens (colors, fonts, sizes, icons) from ``assets/tokens.json`` as CustomTkinter values."""

import json
from functools import cached_property
from pathlib import Path
from typing import Any

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).parent / "assets"
TOKENS_PATH = ASSETS_DIR / "tokens.json"

ColorPair = tuple[str, str]  # (light, dark): the order CustomTkinter expects

_SEMIBOLD_FAMILY = "Segoe UI Semibold"
_ICON_FONT_FILE = "SegoeIcons.ttf"
_ICON_SUPERSAMPLING = 3  # glyphs are drawn larger and scaled down for smooth edges


class Palette:
    """``palette.card`` -> (light, dark) color pair of the token named ``card``."""

    def __init__(self, colors: dict[str, dict[str, str]]) -> None:
        self._colors = colors

    def __getattr__(self, name: str) -> ColorPair:
        try:
            pair = self._colors[name]
        except KeyError:
            raise AttributeError(f"Unknown color token: {name}") from None
        return pair["light"], pair["dark"]


class Theme:
    def __init__(self, tokens_path: Path = TOKENS_PATH) -> None:
        self._tokens: dict[str, Any] = json.loads(tokens_path.read_text(encoding="utf-8"))
        self.colors = Palette(self._tokens["color"])
        self.viewport: dict[str, Any] = self._tokens["viewport"]
        self.size: dict[str, Any] = self._tokens["size"]
        self.radius: dict[str, int] = self._tokens["radius"]
        self.space: list[int] = self._tokens["space"]

    def icon(self, name: str) -> str:
        """The Segoe Fluent Icons glyph for an icon token."""
        return chr(int(self._tokens["icon"][name], 16))

    @cached_property
    def icon_font_family(self) -> str:
        return self._tokens["font"]["icon_family"][0]

    @cached_property
    def mono_family(self) -> str:
        return self._tokens["font"]["mono_family"][0]

    def font(self, role: str) -> ctk.CTkFont:
        """A font for a typography role (page_title, card_title, body, label, caption, stat_value, kbd)."""
        return self._fonts[role]

    @staticmethod
    def resolve(color: ColorPair) -> str:
        """The color of a pair for the current appearance (for widgets that cannot take a pair)."""
        return color[1] if ctk.get_appearance_mode() == "Dark" else color[0]

    def icon_image(self, name: str, color: ColorPair, size: int | None = None) -> ctk.CTkImage:
        """A glyph rendered as an image in the (light, dark) color pair, for buttons and labels."""
        size = size or self.size["icon"]["md"]
        return ctk.CTkImage(
            light_image=self._glyph(name, color[0], size),
            dark_image=self._glyph(name, color[1], size),
            size=(size, size),
        )

    def _glyph(self, name: str, color: str, size: int) -> Image.Image:
        side = size * _ICON_SUPERSAMPLING
        image = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        font = ImageFont.truetype(_ICON_FONT_FILE, side)
        ImageDraw.Draw(image).text((side / 2, side / 2), self.icon(name), font=font, fill=color, anchor="mm")
        return image

    @cached_property
    def _fonts(self) -> dict[str, ctk.CTkFont]:
        fonts = {}
        for role, spec in self._tokens["font"].items():
            if not isinstance(spec, dict):
                continue
            fonts[role] = self._build_font(spec)
        return fonts

    def _build_font(self, spec: dict[str, Any]) -> ctk.CTkFont:
        family = self._tokens["font"]["family"]
        if spec.get("family") == "mono":
            family = self.mono_family
        if spec.get("weight") == "bold" and "Semibold" in spec.get("note", ""):
            return ctk.CTkFont(family=_SEMIBOLD_FAMILY, size=spec["size"])
        return ctk.CTkFont(family=family, size=spec["size"], weight=spec.get("weight", "normal"))
