"""User-tunable settings with their allowed ranges (single source for validation and UI sliders)."""

from dataclasses import dataclass, field

from jestkontrol.domain.appearance import Language, ThemeMode
from jestkontrol.domain.geometry import clamp
from jestkontrol.domain.gestures import GestureType
from jestkontrol.domain.shortcut import DEFAULT_EMERGENCY_SHORTCUT, Shortcut

_PERCENT = 100


@dataclass(frozen=True, slots=True)
class SettingRange:
    minimum: float
    maximum: float
    step: float

    def clamp(self, value: float) -> float:
        return clamp(value, self.minimum, self.maximum)


SETTING_RANGES: dict[str, SettingRange] = {
    "camera_index": SettingRange(0, 9, 1),
    "sensitivity": SettingRange(0.5, 2.0, 0.1),
    "smoothing_percent": SettingRange(0, 95, 5),
    "active_area_margin_percent": SettingRange(0, 30, 1),
    "click_threshold_percent": SettingRange(10, 60, 1),
    "click_cooldown_ms": SettingRange(100, 1000, 50),
    "scroll_speed": SettingRange(1, 10, 1),
    "volume_sensitivity": SettingRange(0.5, 2.0, 0.1),
    "ui_scale_percent": SettingRange(80, 150, 10),
}

RESOLUTION_CHOICES: tuple[tuple[int, int], ...] = ((640, 480), (1280, 720), (1920, 1080))
UI_SCALE_CHOICES: tuple[int, ...] = (80, 90, 100, 110, 125, 150)

ALWAYS_ENABLED_GESTURES = frozenset({GestureType.MOVE})


@dataclass(frozen=True, slots=True)
class Settings:
    camera_index: int = 0
    resolution: tuple[int, int] = (640, 480)
    mirror: bool = True
    show_skeleton: bool = True
    sensitivity: float = 1.2
    smoothing_percent: int = 60
    active_area_margin_percent: int = 15
    click_threshold_percent: int = 30
    click_cooldown_ms: int = 300
    scroll_speed: int = 5
    volume_sensitivity: float = 1.0
    language: Language = Language.TURKISH
    theme: ThemeMode = ThemeMode.DARK
    ui_scale_percent: int = 100
    emergency_shortcut: Shortcut = DEFAULT_EMERGENCY_SHORTCUT
    enabled_gestures: frozenset[GestureType] = field(
        default_factory=lambda: frozenset(GestureType)
    )

    def __post_init__(self) -> None:
        for name, bounds in SETTING_RANGES.items():
            clamped = bounds.clamp(getattr(self, name))
            is_whole_number = isinstance(self.__dataclass_fields__[name].default, int)
            object.__setattr__(self, name, round(clamped) if is_whole_number else round(clamped, 2))
        object.__setattr__(
            self, "enabled_gestures", self.enabled_gestures | ALWAYS_ENABLED_GESTURES
        )

    @property
    def smoothing_alpha(self) -> float:
        """Weight of the newest sample in exponential smoothing (1 = no smoothing)."""
        return 1 - self.smoothing_percent / _PERCENT

    @property
    def active_area_margin(self) -> float:
        return self.active_area_margin_percent / _PERCENT

    @property
    def click_threshold(self) -> float:
        """Pinch distance limit in palm sizes."""
        return self.click_threshold_percent / _PERCENT

    @property
    def click_cooldown_s(self) -> float:
        return self.click_cooldown_ms / 1000

    def is_enabled(self, gesture: GestureType) -> bool:
        return gesture in self.enabled_gestures
