"""Ingestion and normalization helpers.

Implements the "Input Layer" described in Section 7.1 of
AI-ML-or-LLM-RCA.md: heterogeneous telemetry (alarms, KPIs, logs,
topology/config metadata, tickets) is normalized into the common
``Evidence`` representation before any correlation or reasoning happens.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List

from src.common.models import Evidence, EvidenceLayer, EvidenceType

# Maps a raw record's "type" field to the canonical EvidenceType.
_TYPE_ALIASES = {
    "alarm": EvidenceType.ALARM,
    "kpi": EvidenceType.KPI,
    "counter": EvidenceType.KPI,
    "log": EvidenceType.LOG,
    "topology": EvidenceType.TOPOLOGY,
    "config": EvidenceType.CONFIGURATION,
    "configuration": EvidenceType.CONFIGURATION,
    "ticket": EvidenceType.TICKET,
    "engineering_parameter": EvidenceType.ENGINEERING_PARAMETER,
    "engineering": EvidenceType.ENGINEERING_PARAMETER,
}

_LAYER_ALIASES = {
    "l1": EvidenceLayer.PHYSICAL,
    "phy": EvidenceLayer.PHYSICAL,
    "physical": EvidenceLayer.PHYSICAL,
    "l2": EvidenceLayer.MAC_RLC,
    "mac": EvidenceLayer.MAC_RLC,
    "rlc": EvidenceLayer.MAC_RLC,
    "mac_rlc": EvidenceLayer.MAC_RLC,
    "l3": EvidenceLayer.RRC,
    "rrc": EvidenceLayer.RRC,
    "transport": EvidenceLayer.TRANSPORT,
    "core": EvidenceLayer.CORE,
    "configuration": EvidenceLayer.CONFIGURATION,
    "config": EvidenceLayer.CONFIGURATION,
    "service": EvidenceLayer.SERVICE,
}


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)
    if isinstance(value, str):
        # Support both "...Z" ISO strings and plain ISO format.
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise TypeError(f"Unsupported timestamp value: {value!r}")


def normalize_record(record: Dict[str, Any]) -> Evidence:
    """Normalize a single raw telemetry/incident record into ``Evidence``.

    The raw record is expected to contain at least ``source``,
    ``entity_id`` and ``timestamp`` keys. ``type`` and ``layer`` are
    optionally used to classify the evidence; unknown values default to
    ``UNKNOWN``. Any remaining keys are treated as telemetry attributes.
    """
    if "entity_id" not in record:
        raise ValueError("record is missing required field 'entity_id'")
    if "timestamp" not in record:
        raise ValueError("record is missing required field 'timestamp'")

    raw_type = str(record.get("type", "")).strip().lower()
    evidence_type = _TYPE_ALIASES.get(raw_type, EvidenceType.KPI)

    raw_layer = str(record.get("layer", "")).strip().lower()
    layer = _LAYER_ALIASES.get(raw_layer, EvidenceLayer.UNKNOWN)

    reserved = {"source", "entity_id", "timestamp", "type", "layer", "description"}
    attributes = {k: v for k, v in record.items() if k not in reserved}

    return Evidence(
        source=record.get("source", "unknown"),
        evidence_type=evidence_type,
        entity_id=record["entity_id"],
        timestamp=_parse_timestamp(record["timestamp"]),
        attributes=attributes,
        layer=layer,
        description=record.get("description", ""),
    )


def normalize_records(records: Iterable[Dict[str, Any]]) -> List[Evidence]:
    """Normalize a batch of raw records into a list of ``Evidence``.

    Records that cannot be parsed (missing required fields) are skipped
    rather than raising, since ingestion must be resilient to messy,
    heterogeneous operator data.
    """
    normalized: List[Evidence] = []
    for record in records:
        try:
            normalized.append(normalize_record(record))
        except (ValueError, TypeError):
            continue
    return normalized
