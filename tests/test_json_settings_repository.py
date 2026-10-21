import json

from jestkontrol.domain.appearance import Language, ThemeMode
from jestkontrol.domain.gestures import GestureType
from jestkontrol.domain.settings import Settings
from jestkontrol.infrastructure.storage.json_settings_repository import JsonSettingsRepository


def test_missing_file_gives_defaults(tmp_path):
    assert JsonSettingsRepository(tmp_path / "settings.json").load() == Settings()


def test_settings_survive_a_save_and_load_round_trip(tmp_path):
    repository = JsonSettingsRepository(tmp_path / "nested" / "settings.json")
    settings = Settings(
        camera_index=1,
        resolution=(1280, 720),
        mirror=False,
        sensitivity=1.5,
        language=Language.ENGLISH,
        theme=ThemeMode.SYSTEM,
        ui_scale_percent=110,
        enabled_gestures=frozenset({GestureType.LEFT_CLICK, GestureType.SCROLL}),
    )

    repository.save(settings)

    assert repository.load() == settings


def test_unknown_and_missing_keys_are_tolerated(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"sensitivity": 1.7, "from_the_future": True}), encoding="utf-8")

    loaded = JsonSettingsRepository(path).load()

    assert loaded == Settings(sensitivity=1.7)


def test_out_of_range_values_are_clamped_on_load(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"smoothing_percent": 500}), encoding="utf-8")

    assert JsonSettingsRepository(path).load().smoothing_percent == 95


def test_corrupt_file_falls_back_to_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")

    assert JsonSettingsRepository(path).load() == Settings()


def test_invalid_gesture_name_falls_back_to_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"enabled_gestures": ["teleport"]}), encoding="utf-8")

    assert JsonSettingsRepository(path).load() == Settings()
