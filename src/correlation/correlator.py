"""Evidence collection and correlation utilities.

Implements the "Evidence Collection and Correlation" stage described in
Section 7.2 of AI-ML-or-LLM-RCA.md: correlate events across time windows
and network layers/entities rather than analyzing isolated symptoms.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Dict, List

from src.common.models import Evidence, EvidenceGroup


def correlate_by_entity(
    evidences: List[Evidence],
    time_window: timedelta = timedelta(minutes=15),
) -> Dict[str, List[EvidenceGroup]]:
    """Group evidence by ``entity_id``, then split each entity's evidence
    into time-windowed groups.

    Within an entity, evidence items are sorted by timestamp and a new
    group is started whenever the gap to the previous item exceeds
    ``time_window``. This reflects the design requirement to "align
    timestamps across telemetry sources" and "map symptoms to relevant
    network entities".
    """
    by_entity: Dict[str, List[Evidence]] = {}
    for evidence in evidences:
        by_entity.setdefault(evidence.entity_id, []).append(evidence)

    result: Dict[str, List[EvidenceGroup]] = {}
    for entity_id, items in by_entity.items():
        items.sort(key=lambda e: e.timestamp)
        groups: List[EvidenceGroup] = []
        current: EvidenceGroup | None = None
        for item in items:
            if current is None or (
                current.window_end is not None
                and item.timestamp - current.window_end > time_window
            ):
                current = EvidenceGroup(entity_id=entity_id)
                groups.append(current)
            current.add(item)
        result[entity_id] = groups
    return result


def merge_groups(groups: List[EvidenceGroup]) -> EvidenceGroup:
    """Merge multiple evidence groups (e.g. from related entities such as a
    serving cell and its neighbor cells) into a single correlated group."""
    if not groups:
        raise ValueError("cannot merge an empty list of evidence groups")
    merged = EvidenceGroup(entity_id=groups[0].entity_id)
    for group in groups:
        for evidence in group.evidences:
            merged.add(evidence)
    return merged


def find_cross_layer_groups(
    groups_by_entity: Dict[str, List[EvidenceGroup]],
) -> Dict[str, List[EvidenceGroup]]:
    """Filter correlated groups down to those exhibiting cross-layer
    evidence (more than one distinct ``EvidenceLayer``), which the paper
    highlights as the interesting/ambiguous case for RCA (e.g. a radio KPI
    degradation whose real cause lies in transport or core)."""
    filtered: Dict[str, List[EvidenceGroup]] = {}
    for entity_id, groups in groups_by_entity.items():
        cross_layer_groups = [
            g for g in groups if len({e.layer for e in g.evidences}) > 1
        ]
        if cross_layer_groups:
            filtered[entity_id] = cross_layer_groups
    return filtered
