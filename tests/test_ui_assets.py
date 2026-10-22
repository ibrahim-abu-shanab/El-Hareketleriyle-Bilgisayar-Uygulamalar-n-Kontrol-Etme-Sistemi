import json
from pathlib import Path

from jestkontrol.application.gesture_catalog import GESTURE_CATALOG
from jestkontrol.ui.theme import ASSETS_DIR, TOKENS_PATH

DESIGN_TOKENS = Path(__file__).resolve().parents[1] / "design" / "tokens.json"


def test_packaged_tokens_match_the_design_tokens():
    assert json.loads(TOKENS_PATH.read_text(encoding="utf-8")) == json.loads(
        DESIGN_TOKENS.read_text(encoding="utf-8")
    )


def test_every_gesture_has_its_illustration():
    missing = [info.art for info in GESTURE_CATALOG if not (ASSETS_DIR / "art" / f"{info.art}.png").exists()]

    assert missing == []
