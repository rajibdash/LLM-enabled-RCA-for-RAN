import json
from pathlib import Path

import pytest

from src.api.cli import _load_records, main

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_incident.json"


def test_load_records_from_object_with_records_key():
    records = _load_records(str(FIXTURE_PATH))
    assert isinstance(records, list)
    assert len(records) == 3
    assert records[0]["entity_id"] == "cell-0"


def test_load_records_from_bare_list(tmp_path):
    bare_list = [
        {"entity_id": "cell-9", "timestamp": "2026-01-01T00:00:00", "type": "kpi"}
    ]
    path = tmp_path / "bare_list.json"
    path.write_text(json.dumps(bare_list), encoding="utf-8")

    records = _load_records(str(path))

    assert records == bare_list


def test_main_prints_explanation_for_sample_fixture(capsys):
    exit_code = main([str(FIXTURE_PATH), "--incident-id", "cli-test"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "cli-test" in captured.out
    assert "M3" in captured.out


def test_main_defaults_incident_id(capsys):
    exit_code = main([str(FIXTURE_PATH)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "incident-cli" in captured.out


def test_main_requires_input_argument():
    with pytest.raises(SystemExit):
        main([])
