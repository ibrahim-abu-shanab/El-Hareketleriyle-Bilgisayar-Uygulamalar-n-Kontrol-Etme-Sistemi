from dataclasses import replace

import pytest

from jestkontrol.domain.gestures import GestureType
from jestkontrol.domain.settings import SETTING_RANGES, Settings


def test_defaults_match_design():
    settings = Settings()

    assert settings.resolution == (640, 480)
    assert settings.sensitivity == 1.2
    assert settings.smoothing_percent == 60
    assert settings.click_threshold == pytest.approx(0.30)
    assert settings.click_cooldown_s == pytest.approx(0.3)
    assert settings.active_area_margin == pytest.approx(0.15)


def test_derived_smoothing_alpha():
    assert Settings(smoothing_percent=60).smoothing_alpha == pytest.approx(0.4)
    assert Settings(smoothing_percent=0).smoothing_alpha == 1


@pytest.mark.parametrize("name", sorted(SETTING_RANGES))
def test_out_of_range_values_are_clamped(name):
    bounds = SETTING_RANGES[name]

    too_low = Settings(**{name: bounds.minimum - 1})
    too_high = Settings(**{name: bounds.maximum + 1})

    assert getattr(too_low, name) == bounds.minimum
    assert getattr(too_high, name) == bounds.maximum


def test_cursor_move_gesture_cannot_be_disabled():
    settings = Settings(enabled_gestures=frozenset({GestureType.SCROLL}))

    assert settings.is_enabled(GestureType.MOVE)
    assert settings.is_enabled(GestureType.SCROLL)
    assert not settings.is_enabled(GestureType.DRAG)


def test_replace_revalidates():
    assert replace(Settings(), sensitivity=99).sensitivity == 2.0
