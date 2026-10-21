"""Looks up UI text for the current language and formats numbers the way that language writes them."""

import logging
from collections.abc import Callable, Mapping
from datetime import date, datetime

from jestkontrol.application.i18n.catalog_en import ENGLISH
from jestkontrol.application.i18n.catalog_tr import TURKISH
from jestkontrol.application.observable import Listeners, Unsubscribe
from jestkontrol.domain.appearance import Language

logger = logging.getLogger(__name__)

CATALOGS: dict[Language, Mapping[str, str]] = {
    Language.TURKISH: TURKISH,
    Language.ENGLISH: ENGLISH,
}
FALLBACK_LANGUAGE = Language.TURKISH
DATE_TIME_FORMAT = "%d.%m.%Y %H:%M"
TIME_FORMAT = "%H:%M"


class Translator:
    def __init__(self, language: Language = FALLBACK_LANGUAGE) -> None:
        self._language = language
        self._listeners = Listeners()

    @property
    def language(self) -> Language:
        return self._language

    def set_language(self, language: Language) -> None:
        if language is self._language:
            return
        self._language = language
        self._listeners.notify(language)

    def subscribe(self, listener: Callable[[Language], None]) -> Unsubscribe:
        return self._listeners.add(listener)

    def t(self, key: str, **params: object) -> str:
        text = CATALOGS[self._language].get(key) or CATALOGS[FALLBACK_LANGUAGE].get(key)
        if text is None:
            logger.warning("Missing translation key: %s", key)
            return key
        return text.format(**params) if params else text

    def number(self, value: float, decimals: int = 1) -> str:
        return f"{value:.{decimals}f}".replace(".", self.t("format.decimal_separator"))

    def percent(self, value: float, decimals: int = 0) -> str:
        """``value`` is already a percentage (60 -> '%60' in Turkish, '60%' in English)."""
        return self.t("format.percent", value=self.number(value, decimals))

    def multiplier(self, value: float) -> str:
        return self.t("format.multiplier", value=self.number(value, 1))

    def milliseconds(self, value: float) -> str:
        return self.t("format.milliseconds", value=round(value))

    def date_time(self, moment: datetime) -> str:
        return moment.strftime(DATE_TIME_FORMAT)

    def relative_day_time(self, moment: datetime, today: date | None = None) -> str:
        """'bugün 14:47' for today, the full date otherwise."""
        if moment.date() == (today or date.today()):
            return f"{self.t('format.today')} {moment.strftime(TIME_FORMAT)}"
        return self.date_time(moment)
