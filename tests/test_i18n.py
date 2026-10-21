from datetime import date, datetime

import pytest

from jestkontrol.application.i18n.catalog_en import ENGLISH
from jestkontrol.application.i18n.catalog_tr import TURKISH
from jestkontrol.application.i18n.translator import Translator
from jestkontrol.domain.appearance import Language


def test_both_catalogs_define_exactly_the_same_keys():
    assert set(TURKISH) == set(ENGLISH)


def test_both_catalogs_use_the_same_placeholders():
    import string

    def fields(text):
        return {name for _, name, _, _ in string.Formatter().parse(text) if name}

    mismatches = [key for key in TURKISH if fields(TURKISH[key]) != fields(ENGLISH[key])]

    assert mismatches == []


def test_translates_in_the_current_language_and_notifies_on_change():
    translator = Translator(Language.TURKISH)
    changes = []
    translator.subscribe(changes.append)

    assert translator.t("action.start") == "Başlat"
    translator.set_language(Language.ENGLISH)
    translator.set_language(Language.ENGLISH)  # no change, no notification

    assert translator.t("action.start") == "Start"
    assert changes == [Language.ENGLISH]


def test_parameters_are_substituted():
    assert Translator(Language.ENGLISH).t("event.mode", mode="Mouse") == "Mode: Mouse"


def test_missing_key_returns_the_key_itself():
    assert Translator().t("no.such.key") == "no.such.key"


def test_number_formatting_follows_the_language():
    turkish, english = Translator(Language.TURKISH), Translator(Language.ENGLISH)

    assert (turkish.number(29.4), english.number(29.4)) == ("29,4", "29.4")
    assert (turkish.percent(60), english.percent(60)) == ("%60", "60%")
    assert (turkish.multiplier(1.2), english.multiplier(1.2)) == ("1,2×", "1.2×")
    assert turkish.milliseconds(23.6) == "24 ms"


def test_dates():
    translator = Translator(Language.TURKISH)
    moment = datetime(2026, 10, 14, 14, 52)

    assert translator.date_time(moment) == "14.10.2026 14:52"
    assert translator.relative_day_time(moment, today=date(2026, 10, 14)) == "bugün 14:52"
    assert translator.relative_day_time(moment, today=date(2026, 10, 15)) == "14.10.2026 14:52"


@pytest.mark.parametrize("language", list(Language))
def test_every_catalog_formats_without_errors(language):
    translator = Translator(language)

    assert translator.t("tests.accuracy.wrong_note", trial=14, detected="x") != ""
