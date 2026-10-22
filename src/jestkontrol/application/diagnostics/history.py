"""Persistent history of finished diagnostics and its CSV export."""

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from jestkontrol.application.diagnostics.records import DiagnosticKind, DiagnosticRecord
from jestkontrol.application.observable import Listeners, Unsubscribe

MAX_RECORDS = 200


class DiagnosticsRepository(Protocol):
    def load(self) -> list[DiagnosticRecord]: ...

    def save(self, records: list[DiagnosticRecord]) -> None: ...


class ResultsExporter(Protocol):
    def export(self, records: list[DiagnosticRecord], path: Path) -> None: ...


class DiagnosticsHistory:
    def __init__(self, repository: DiagnosticsRepository, exporter: ResultsExporter) -> None:
        self._repository = repository
        self._exporter = exporter
        self._lock = threading.Lock()
        self._records = sorted(repository.load(), key=lambda r: r.recorded_at, reverse=True)
        self._listeners = Listeners()

    def subscribe(self, listener: Callable[[], None]) -> Unsubscribe:
        return self._listeners.add(listener)

    def records(self) -> list[DiagnosticRecord]:
        """Newest first."""
        with self._lock:
            return list(self._records)

    def latest(self, kind: DiagnosticKind) -> DiagnosticRecord | None:
        return next((r for r in self.records() if r.kind is kind), None)

    def add(self, record: DiagnosticRecord) -> None:
        with self._lock:
            self._records = [record, *self._records][:MAX_RECORDS]
        self._persist_and_notify()

    def clear(self) -> None:
        with self._lock:
            self._records = []
        self._persist_and_notify()

    def export(self, path: Path) -> int:
        """Writes all records to ``path`` and returns how many were exported."""
        records = self.records()
        self._exporter.export(records, path)
        return len(records)

    def _persist_and_notify(self) -> None:
        self._repository.save(self.records())
        self._listeners.notify()
