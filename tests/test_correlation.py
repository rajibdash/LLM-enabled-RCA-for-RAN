from datetime import datetime, timedelta

from src.common.models import Evidence, EvidenceLayer, EvidenceType
from src.correlation.correlator import (
    correlate_by_entity,
    find_cross_layer_groups,
    merge_groups,
)


def _evidence(entity_id, minute, layer=EvidenceLayer.UNKNOWN, evidence_type=EvidenceType.KPI):
    return Evidence(
        source="test",
        evidence_type=evidence_type,
        entity_id=entity_id,
        timestamp=datetime(2026, 1, 1, 0, 0, 0) + timedelta(minutes=minute),
        layer=layer,
    )


def test_correlate_by_entity_groups_by_entity():
    evidences = [
        _evidence("cell-1", 0),
        _evidence("cell-1", 1),
        _evidence("cell-2", 0),
    ]

    groups = correlate_by_entity(evidences)

    assert set(groups.keys()) == {"cell-1", "cell-2"}
    assert len(groups["cell-1"][0].evidences) == 2
    assert len(groups["cell-2"][0].evidences) == 1


def test_correlate_by_entity_splits_on_large_time_gap():
    evidences = [
        _evidence("cell-1", 0),
        _evidence("cell-1", 1),
        _evidence("cell-1", 100),  # far outside the default 15-minute window
    ]

    groups = correlate_by_entity(evidences, time_window=timedelta(minutes=15))

    cell_groups = groups["cell-1"]
    assert len(cell_groups) == 2
    assert len(cell_groups[0].evidences) == 2
    assert len(cell_groups[1].evidences) == 1


def test_merge_groups_combines_evidence_and_preserves_window():
    evidences = [
        _evidence("cell-1", 0),
        _evidence("cell-1", 1),
        _evidence("cell-2", 2),
    ]
    groups = correlate_by_entity(evidences)
    all_groups = [g for gs in groups.values() for g in gs]

    merged = merge_groups(all_groups)

    assert len(merged.evidences) == 3
    assert merged.window_start == datetime(2026, 1, 1, 0, 0, 0)
    assert merged.window_end == datetime(2026, 1, 1, 0, 2, 0)


def test_find_cross_layer_groups_filters_single_layer_groups():
    evidences = [
        _evidence("cell-1", 0, layer=EvidenceLayer.PHYSICAL),
        _evidence("cell-1", 1, layer=EvidenceLayer.PHYSICAL),
    ]
    cross_layer_evidences = [
        _evidence("cell-2", 0, layer=EvidenceLayer.PHYSICAL),
        _evidence("cell-2", 1, layer=EvidenceLayer.TRANSPORT),
    ]

    groups = correlate_by_entity(evidences + cross_layer_evidences)
    filtered = find_cross_layer_groups(groups)

    assert "cell-1" not in filtered
    assert "cell-2" in filtered
