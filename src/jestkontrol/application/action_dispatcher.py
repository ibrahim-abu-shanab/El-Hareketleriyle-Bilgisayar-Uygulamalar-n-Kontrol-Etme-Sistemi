"""Routes gesture events to the handler registered for their type."""

import logging
from collections.abc import Callable, Iterable

from jestkontrol.domain.gestures import GestureEvent

logger = logging.getLogger(__name__)


class ActionDispatcher:
    def __init__(self) -> None:
        self._handlers: dict[type[GestureEvent], Callable[[GestureEvent], None]] = {}

    def register[E: GestureEvent](
        self, event_type: type[E], handler: Callable[[E], None]
    ) -> None:
        self._handlers[event_type] = handler  # type: ignore[assignment]

    def dispatch(self, events: Iterable[GestureEvent]) -> None:
        for event in events:
            handler = self._handlers.get(type(event))
            if handler is None:
                logger.warning("No handler registered for %s", type(event).__name__)
                continue
            handler(event)
