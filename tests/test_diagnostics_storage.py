import csv
from datetime import datetime

from jestkontrol.application.diagnostics.records import DiagnosticKind, DiagnosticRecord
from jestkontrol.infrastructure.storage.csv_results_exporter import HEADER, CsvResultsExporter
from jestkontrol.infrastructure.storage.json_diagnostics_repository import (
    JsonDiagnosticsRepository,
)

RECORDS = [
    DiagnosticRecord(
        datetime(2026, 10, 14, 14, 52),
        DiagnosticKind.ACCURACY,
        True,
        {"gesture": "left_click", "trials": 20},
        {"correct": 19, "accuracy": 0.95},
    ),
    DiagnosticRecord(
        datetime(2026, 10, 14, 14, 47),
        DiagnosticKind.FPS,
        False,
        {"duration_s": 30, "width": 640, "height": 480},
        {"average": 21.6},
        (22.0, 21.0, 21.8),
    ),
]


def test_records_survive_a_save_and_load_round_trip(tmp_path):
    repository = JsonDiagnosticsRepository(tmp_path / "sub" / "history.json")

    repository.save(RECORDS)

    assert repository.load() == RECORDS


def test_missing_file_gives_an_empty_history(tmp_path):
    assert JsonDiagnosticsRepository(tmp_path / "none.json").load() == []


def test_corrupt_file_gives_an_empty_history(tmp_path):
    path = tmp_path / "history.json"
    path.write_text('[{"kind": "nonsense"}]', encoding="utf-8")

    assert JsonDiagnosticsRepository(path).load() == []


def test_csv_export_has_header_and_one_row_per_record(tmp_path):
    path = tmp_path / "out" / "results.csv"

    CsvResultsExporter().export(RECORDS, path)

    assert path.read_bytes().startswith(b"\xef\xbb\xbf")  # BOM so Excel detects UTF-8
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.reader(file, delimiter=";"))
    assert tuple(rows[0]) == HEADER
    assert rows[1] == [
        "2026-10-14 14:52:00",
        "accuracy",
        "yes",
        "gesture=left_click, trials=20",
        "correct=19, accuracy=0.95",
        "",
    ]
    assert rows[2][2] == "no" and rows[2][5] == "22 21 21.8" and len(rows) == 3


def test_files_from_older_versions_without_series_still_load(tmp_path):
    path = tmp_path / "history.json"
    path.write_text(
        '[{"recorded_at": "2026-10-14T14:47:00", "kind": "fps", "passed": true,'
        ' "parameters": {}, "metrics": {}}]',
        encoding="utf-8",
    )

    [record] = JsonDiagnosticsRepository(path).load()

    assert record.series == ()
