"""Reasoning engine: candidate root-cause generation and ranking.

Implements the "Hypothesis Generation" stage (Section 7.4) using the
same diagnostic-check style as SEKA-FT's decision-path control
(Section 4.2): structured evidence is first reduced to a small set of
interpretable boolean checks (mobility, scheduling, handovers, coverage
distance, downtilt, interference, transport), and those checks are used
to generate and score candidate root causes instead of jumping straight
to a single unsupported conclusion.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from src.common.models import EvidenceGroup, EvidenceLayer, RootCauseHypothesis
from src.retrieval.retriever import KnowledgeBase, default_documents


@dataclass
class DiagnosticThresholds:
    """Thresholds for the deterministic diagnostic checks, mirroring the
    paper's example definitions (e.g. "vehicle speed exceeds 40 km/h",
    "average scheduled RBs below 160")."""

    high_speed_kmh: float = 40.0
    low_rb_count: float = 160.0
    frequent_handover_count: int = 3
    overshoot_distance_km: float = 1.0
    aggressive_downtilt_deg: float = 20.0


def run_diagnostic_checks(
    group: EvidenceGroup, thresholds: DiagnosticThresholds | None = None
) -> Dict[str, bool]:
    """Reduce an evidence group to a compact set of interpretable
    diagnostic checks (Step 1 of SEKA-FT's two-step explanation design)."""
    thresholds = thresholds or DiagnosticThresholds()
    checks: Dict[str, bool] = {}

    speeds = [e.get("ue_speed_kmh") for e in group.evidences if e.get("ue_speed_kmh") is not None]
    checks["speed_check"] = bool(speeds) and max(speeds) > thresholds.high_speed_kmh

    rbs = [e.get("scheduled_rbs") for e in group.evidences if e.get("scheduled_rbs") is not None]
    checks["low_rb_check"] = bool(rbs) and (sum(rbs) / len(rbs)) < thresholds.low_rb_count

    handover_counts = [
        e.get("handover_count") for e in group.evidences if e.get("handover_count") is not None
    ]
    checks["handover_check"] = (
        bool(handover_counts) and max(handover_counts) >= thresholds.frequent_handover_count
    )

    distances = [
        e.get("ue_distance_km") for e in group.evidences if e.get("ue_distance_km") is not None
    ]
    checks["distance_check"] = bool(distances) and max(distances) > thresholds.overshoot_distance_km

    downtilts = [
        e.get("mechanical_downtilt_deg") for e in group.evidences if e.get("mechanical_downtilt_deg") is not None
    ]
    checks["downtilt_check"] = bool(downtilts) and max(downtilts) > thresholds.aggressive_downtilt_deg

    pci_collisions = [e for e in group.evidences if e.get("pci_mod_collision") is True]
    checks["interference_check"] = bool(pci_collisions)

    cross_layer = len({e.layer for e in group.evidences}) > 1
    checks["transport_check"] = cross_layer and any(
        e.layer == EvidenceLayer.TRANSPORT for e in group.evidences
    )

    return checks


# Mapping of check name -> (hypothesis code, description, layer, kb tag)
_CHECK_TO_HYPOTHESIS = {
    "speed_check": ("M4", "Excessive UE mobility speed degrades throughput", EvidenceLayer.MAC_RLC, "mobility"),
    "low_rb_check": ("M1", "Insufficient scheduled resource blocks", EvidenceLayer.MAC_RLC, "scheduling"),
    "handover_check": ("M2", "Frequent handovers destabilize the connection", EvidenceLayer.RRC, "handover"),
    "distance_check": ("M6", "Serving cell coverage overshoot", EvidenceLayer.PHYSICAL, "coverage"),
    "downtilt_check": ("M3", "Aggressive serving-cell downtilt causes edge coverage loss", EvidenceLayer.PHYSICAL, "downtilt"),
    "interference_check": ("M5", "PCI collision causes neighbor-cell interference", EvidenceLayer.PHYSICAL, "interference"),
    "transport_check": ("M8", "Transport-layer bottleneck affecting radio KPIs", EvidenceLayer.TRANSPORT, "transport"),
}


class ReasoningEngine:
    """Generates and ranks candidate root-cause hypotheses from correlated
    evidence, grounding each candidate in retrieved domain knowledge."""

    def __init__(
        self,
        knowledge_base: KnowledgeBase | None = None,
        thresholds: DiagnosticThresholds | None = None,
    ) -> None:
        self.knowledge_base = knowledge_base or KnowledgeBase(default_documents())
        self.thresholds = thresholds or DiagnosticThresholds()

    def generate_hypotheses(self, group: EvidenceGroup) -> List[RootCauseHypothesis]:
        """Generate candidate root causes from a correlated evidence group.

        Every check that fires produces a corresponding hypothesis with an
        initial score and supporting evidence drawn from the knowledge
        base; checks that do not fire still appear in every hypothesis'
        ``checks`` dict so later verification can "rule out" alternatives,
        matching the paper's decision-path pruning behavior.
        """
        checks = run_diagnostic_checks(group, self.thresholds)
        hypotheses: List[RootCauseHypothesis] = []

        for check_name, (code, description, layer, tag) in _CHECK_TO_HYPOTHESIS.items():
            if not checks.get(check_name):
                continue
            kb_hits = self.knowledge_base.search_by_tag(tag)
            supporting = [doc.title for doc in kb_hits]
            hypotheses.append(
                RootCauseHypothesis(
                    code=code,
                    description=description,
                    layer=layer,
                    score=1.0,  # base score; refined during ranking/validation
                    supporting_evidence=supporting,
                    checks=dict(checks),
                )
            )

        if not hypotheses:
            # No specific check fired: fall back to a generic, low-confidence
            # "undetermined" hypothesis rather than fabricating a cause.
            hypotheses.append(
                RootCauseHypothesis(
                    code="M0",
                    description="No single dominant cause identified from available checks",
                    layer=EvidenceLayer.UNKNOWN,
                    score=0.1,
                    checks=dict(checks),
                )
            )

        return hypotheses

    def rank(self, hypotheses: List[RootCauseHypothesis]) -> List[RootCauseHypothesis]:
        """Rank candidates by score, descending. Ties are broken by the
        amount of supporting evidence (more supporting evidence ranks
        higher)."""
        return sorted(
            hypotheses,
            key=lambda h: (h.score, len(h.supporting_evidence)),
            reverse=True,
        )

    def generate_and_rank(self, group: EvidenceGroup) -> List[RootCauseHypothesis]:
        return self.rank(self.generate_hypotheses(group))
