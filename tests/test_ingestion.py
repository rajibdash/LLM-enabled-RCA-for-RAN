from datetime import datetime

import pytest

from src.common.models import EvidenceLayer, EvidenceType
from src.ingestion.normalizer import normalize_record, normalize_records


def test_normalize_record_basic_fields():
    record = {
        "source": "oss_alarms",
        "entity_id": "cell-1",
        "timestamp": "2026-01-01T00:00:00",
        "type": "alarm",
        "layer": "l1",
        "description": "Downlink throughput degraded",
        "severity": "major",
    }

    evidence = normalize_record(record)

    assert evidence.source == "oss_alarms"
    assert evidence.entity_id == "cell-1"
    assert evidence.timestamp == datetime(2026, 1, 1, 0, 0, 0)
    assert evidence.evidence_type == EvidenceType.ALARM
    assert evidence.layer == EvidenceLayer.PHYSICAL
    assert evidence.description == "Downlink throughput degraded"
    # Non-reserved keys become attributes.
    assert evidence.attributes == {"severity": "major"}


def test_normalize_record_defaults_unknown_type_and_layer():
    record = {
        "entity_id": "cell-2",
        "timestamp": "2026-01-01T00:00:00",
        "scheduled_rbs": 177.0,
    }

    evidence = normalize_record(record)

    assert evidence.source == "unknown"
    assert evidence.evidence_type == EvidenceType.KPI
    assert evidence.layer == EvidenceLayer.UNKNOWN
    assert evidence.get("scheduled_rbs") == 177.0
    assert evidence.get("missing_key", "default") == "default"


@pytest.mark.parametrize("missing_field", ["entity_id", "timestamp"])
def test_normalize_record_requires_entity_and_timestamp(missing_field):
    record = {
        "entity_id": "cell-1",
        "timestamp": "2026-01-01T00:00:00",
    }
    del record[missing_field]

    with pytest.raises(ValueError):
        normalize_record(record)


def test_normalize_records_skips_bad_records():
    records = [
        {"entity_id": "cell-1", "timestamp": "2026-01-01T00:00:00"},
        {"entity_id": "cell-2"},  # missing timestamp -> skipped
        {"timestamp": "2026-01-01T00:00:00"},  # missing entity_id -> skipped
        {"entity_id": "cell-3", "timestamp": "not-a-timestamp"},  # bad timestamp -> skipped
    ]

    normalized = normalize_records(records)

    assert len(normalized) == 1
    assert normalized[0].entity_id == "cell-1"


def test_normalize_record_accepts_epoch_timestamp():
    record = {"entity_id": "cell-1", "timestamp": 0}
    evidence = normalize_record(record)
    assert evidence.timestamp == datetime.fromtimestamp(0)
