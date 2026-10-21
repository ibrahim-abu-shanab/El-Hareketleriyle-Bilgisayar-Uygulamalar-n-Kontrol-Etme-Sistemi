"""Diagnostics history persisted as a JSON file."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from jestkontrol.application.diagnostics.records import DiagnosticKind, DiagnosticRecord

logger = logging.getLogger(__name__)


class JsonDiagnosticsRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> list[DiagnosticRecord]:
        try:
            rows = json.loads(self._path.read_text(encoding="utf-8"))
            return [_decode(row) for row in rows]
        except FileNotFoundError:
            return []
        except (OSError, ValueError, KeyError, TypeError):
            logger.warning("Diagnostics history %s is unreadable; starting empty", self._path)
            return []

    def save(self, records: list[DiagnosticRecord]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([_encode(r) for r in records], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def _encode(record: DiagnosticRecord) -> dict[str, Any]:
    return {
        "recorded_at": record.recorded_at.isoformat(timespec="seconds"),
        "kind": record.kind.value,
        "passed": record.passed,
        "parameters": record.parameters,
        "metrics": record.metrics,
        "series": list(record.series),
    }


def _decode(row: dict[str, Any]) -> DiagnosticRecord:
    return DiagnosticRecord(
        datetime.fromisoformat(row["recorded_at"]),
        DiagnosticKind(row["kind"]),
        bool(row["passed"]),
        dict(row["parameters"]),
        dict(row["metrics"]),
        tuple(float(value) for value in row.get("series", ())),  # absent in files from older versions
    )
