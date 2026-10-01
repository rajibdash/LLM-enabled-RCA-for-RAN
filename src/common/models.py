"""Shared data models for telecom evidence and RCA hypotheses.

These lightweight dataclasses implement the "canonical evidence
representation" described in the paper's design (Section 7.1 / 4.1 of
AI-ML-or-LLM-RCA.md): heterogeneous telemetry is normalized into a common
structure before any reasoning takes place.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class EvidenceLayer(str, Enum):
    """Network layer / domain associated with a piece of evidence."""

    PHYSICAL = "physical"
    MAC_RLC = "mac_rlc"
    RRC = "rrc"
    TRANSPORT = "transport"
    CORE = "core"
    CONFIGURATION = "configuration"
    SERVICE = "service"
    UNKNOWN = "unknown"


class EvidenceType(str, Enum):
    """Kind of telemetry source the evidence originated from."""

    ALARM = "alarm"
    KPI = "kpi"
    LOG = "log"
    TOPOLOGY = "topology"
    CONFIGURATION = "configuration"
    TICKET = "ticket"
    ENGINEERING_PARAMETER = "engineering_parameter"


@dataclass
class Evidence:
    """A single, normalized piece of telecom evidence.

    Attributes:
        source: Where the evidence came from, e.g. ``"gnb_alarm_feed"``.
        evidence_type: The kind of evidence (alarm, KPI, log, ...).
        layer: The network layer/domain this evidence relates to.
        entity_id: Identifier of the affected network entity (cell, site,
            gNodeB, service, etc.).
        timestamp: When the evidence was observed.
        attributes: Arbitrary key/value telemetry payload, e.g.
            ``{"downlink_throughput_mbps": 420.88}``.
        description: Optional human-readable description (e.g. alarm text,
            ticket note).
    """

    source: str
    evidence_type: EvidenceType
    entity_id: str
    timestamp: datetime
    attributes: Dict[str, Any] = field(default_factory=dict)
    layer: EvidenceLayer = EvidenceLayer.UNKNOWN
    description: str = ""

    def get(self, key: str, default: Any = None) -> Any:
        """Convenience accessor into ``attributes``."""
        return self.attributes.get(key, default)


@dataclass
class EvidenceGroup:
    """A set of correlated evidence sharing a time window / entity scope."""

    entity_id: str
    evidences: List[Evidence] = field(default_factory=list)
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None

    def add(self, evidence: Evidence) -> None:
        self.evidences.append(evidence)
        if self.window_start is None or evidence.timestamp < self.window_start:
            self.window_start = evidence.timestamp
        if self.window_end is None or evidence.timestamp > self.window_end:
            self.window_end = evidence.timestamp

    def by_layer(self, layer: EvidenceLayer) -> List[Evidence]:
        return [e for e in self.evidences if e.layer == layer]

    def by_type(self, evidence_type: EvidenceType) -> List[Evidence]:
        return [e for e in self.evidences if e.evidence_type == evidence_type]


@dataclass
class RootCauseHypothesis:
    """A candidate root cause, following the paper's hypothesis-generation
    and evidence-grounded verification stages."""

    code: str
    description: str
    layer: EvidenceLayer = EvidenceLayer.UNKNOWN
    score: float = 0.0
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    checks: Dict[str, bool] = field(default_factory=dict)
    verified: bool = False

    def explain(self) -> str:
        """Produce a short, explainable-output style summary."""
        lines = [f"Root cause candidate {self.code}: {self.description}"]
        if self.checks:
            checks_str = ", ".join(f"{k}={v}" for k, v in self.checks.items())
            lines.append(f"Diagnostic checks: {checks_str}")
        if self.supporting_evidence:
            lines.append("Supporting evidence: " + "; ".join(self.supporting_evidence))
        if self.contradicting_evidence:
            lines.append(
                "Contradicting evidence: " + "; ".join(self.contradicting_evidence)
            )
        lines.append(f"Confidence score: {self.score:.3f} (verified={self.verified})")
        return "\n".join(lines)


@dataclass
class RCAResult:
    """Final, ranked output of the RCA pipeline for a given incident."""

    incident_id: str
    ranked_hypotheses: List[RootCauseHypothesis] = field(default_factory=list)

    @property
    def top_hypothesis(self) -> Optional[RootCauseHypothesis]:
        return self.ranked_hypotheses[0] if self.ranked_hypotheses else None

    def explain(self) -> str:
        if not self.ranked_hypotheses:
            return f"Incident {self.incident_id}: no root cause candidates found."
        lines = [f"Incident {self.incident_id} — Root Cause Analysis"]
        for rank, hyp in enumerate(self.ranked_hypotheses, start=1):
            lines.append(f"\n#{rank} (score={hyp.score:.3f})")
            lines.append(hyp.explain())
        return "\n".join(lines)
