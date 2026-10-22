"""Exports diagnostics to CSV that opens correctly in Excel (UTF-8 with BOM, ';' separator)."""

import csv
from pathlib import Path

from jestkontrol.application.diagnostics.records import DiagnosticRecord

DELIMITER = ";"
HEADER = ("recorded_at", "test", "passed", "parameters", "metrics", "fps_per_second")


class CsvResultsExporter:
    def export(self, records: list[DiagnosticRecord], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file, delimiter=DELIMITER)
            writer.writerow(HEADER)
            for record in records:
                writer.writerow(
                    (
                        record.recorded_at.strftime("%Y-%m-%d %H:%M:%S"),
                        record.kind.value,
                        "yes" if record.passed else "no",
                        _join(record.parameters),
                        _join(record.metrics),
                        " ".join(f"{value:g}" for value in record.series),
                    )
                )


def _join(values: dict[str, object]) -> str:
    return ", ".join(f"{name}={value}" for name, value in values.items())
