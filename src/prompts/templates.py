"""Prompt templates and prompt builders for LLM-enabled RCA.

Implements the canonical-context-structuring idea from Section 4.1 of
AI-ML-or-LLM-RCA.md: evidence is rendered into fixed semantic slots
(Bottleneck Snapshot, UE Global State, Trajectory-Level Events,
Engineering Parameters) so that an LLM (or a human reviewer) always sees
a stable, comparable context regardless of the underlying raw telemetry
format.
"""
from __future__ import annotations

from typing import Iterable, List

from src.common.models import Evidence, EvidenceGroup, RootCauseHypothesis

SYSTEM_PROMPT = (
    "You are a telecom network root-cause-analysis assistant. You must "
    "reason step by step over the structured evidence provided, generate "
    "multiple candidate root causes, and verify each candidate against "
    "the evidence before producing a final, explainable diagnosis. Do not "
    "speculate beyond what the evidence supports."
)


def format_evidence_block(evidence: Evidence) -> str:
    """Render a single evidence item as one canonical context line."""
    attrs = ", ".join(f"{k}={v}" for k, v in evidence.attributes.items())
    parts = [
        f"[{evidence.evidence_type.value}]",
        f"entity={evidence.entity_id}",
        f"layer={evidence.layer.value}",
        f"time={evidence.timestamp.isoformat()}",
    ]
    if attrs:
        parts.append(attrs)
    if evidence.description:
        parts.append(f"description={evidence.description!r}")
    return " ".join(parts)


def build_context_block(group: EvidenceGroup) -> str:
    """Build a canonical, structured context block for an evidence group,
    mirroring the paper's "Bottleneck Snapshot / UE Global State /
    Trajectory-Level Events" style presentation."""
    lines = [f"Entity: {group.entity_id}"]
    if group.window_start and group.window_end:
        lines.append(f"Window: {group.window_start.isoformat()} -> {group.window_end.isoformat()}")
    lines.append("Evidence:")
    for evidence in group.evidences:
        lines.append(f"  - {format_evidence_block(evidence)}")
    return "\n".join(lines)


def build_hypothesis_prompt(
    group: EvidenceGroup, candidate_descriptions: Iterable[str]
) -> str:
    """Build a full RCA prompt that asks the model to select the most
    likely root cause from a list of candidates, given structured
    evidence — directly modeled on the paper's illustrative SEKA-FT
    input/output sample."""
    context = build_context_block(group)
    candidates = "\n".join(
        f"  {chr(ord('A') + i)}: {desc}"
        for i, desc in enumerate(candidate_descriptions)
    )
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Context:\n{context}\n\n"
        f"Candidate root causes:\n{candidates}\n\n"
        "Instruction: Provide step-by-step diagnostic checks, then state "
        "the final decision with supporting and contradicting evidence."
    )


def build_explanation(hypothesis: RootCauseHypothesis) -> str:
    """Build an evidence-grounded, explainable-output style narrative for
    a scored/verified hypothesis (Section 7.6)."""
    return hypothesis.explain()


def build_candidate_summary(hypotheses: List[RootCauseHypothesis]) -> str:
    """Summarize all candidates considered, including ones that were
    ultimately ruled out — supports operator trust/auditability."""
    lines = ["Candidate root causes considered:"]
    for hyp in hypotheses:
        status = "VERIFIED" if hyp.verified else "ruled out / unverified"
        lines.append(f"  - {hyp.code} ({status}, score={hyp.score:.3f}): {hyp.description}")
    return "\n".join(lines)
