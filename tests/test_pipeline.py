import json
from pathlib import Path

from src.api.cli import run_pipeline

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_incident.json"


def _load_sample_records():
    with open(FIXTURE_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)["records"]


def test_pipeline_end_to_end_smoke():
    records = _load_sample_records()

    result = run_pipeline(records, incident_id="smoke-test")

    assert result.incident_id == "smoke-test"
    assert result.ranked_hypotheses, "pipeline should produce at least one hypothesis"

    top = result.top_hypothesis
    assert top is not None
    # The fixture reproduces the paper's downtilt scenario: all mobility/RB/
    # handover/distance checks are False, so the top verified hypothesis
    # should be the aggressive-downtilt cause (M3).
    assert top.code == "M3"
    assert top.verified is True

    explanation = result.explain()
    assert "smoke-test" in explanation
    assert "M3" in explanation


def test_pipeline_handles_empty_input_gracefully():
    result = run_pipeline([], incident_id="empty-test")
    assert result.ranked_hypotheses == []
    assert "no root cause candidates" in result.explain()


def test_pipeline_skips_unparsable_records_without_crashing():
    records = [
        {"entity_id": "cell-1"},  # missing timestamp
        {
            "entity_id": "cell-1",
            "timestamp": "2026-01-01T00:00:00",
            "type": "kpi",
            "ue_speed_kmh": 10.0,
        },
    ]

    result = run_pipeline(records, incident_id="partial-test")

    assert result.ranked_hypotheses  # still produces a result from the valid record
