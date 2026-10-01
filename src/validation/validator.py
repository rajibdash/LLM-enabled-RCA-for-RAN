"""Evidence-grounded verification / validation logic.

Implements the "Evidence-Grounded Verification" stage (Section 7.5):
each candidate root cause must be checked against the observed evidence
(temporal alignment, layer consistency, contradictions) before it can be
considered verified, rather than trusting the reasoning engine's output
at face value.
"""
from __future__ import annotations

from typing import List

from src.common.models import EvidenceGroup, RootCauseHypothesis

#: Minimum score (after contradiction penalties) required to mark a
#: hypothesis as verified.
VERIFICATION_THRESHOLD = 0.5


def verify_hypothesis(
    hypothesis: RootCauseHypothesis, group: EvidenceGroup
) -> RootCauseHypothesis:
    """Validate a single hypothesis against its originating evidence group.

    - Checks that the hypothesis' own ``checks`` are internally consistent
      (i.e. the check backing this hypothesis actually fired).
    - Penalizes the score for every *other* check that also fired, since
      multiple simultaneous positive checks indicate ambiguous evidence
      that should lower confidence in any single explanation.
    - Flags a contradiction if the evidence group has no evidence at all
      for the hypothesis' declared layer.
    """
    checks = hypothesis.checks or {}
    positive_checks = [name for name, value in checks.items() if value]

    if not positive_checks:
        hypothesis.verified = False
        hypothesis.contradicting_evidence.append(
            "No diagnostic check supports this hypothesis"
        )
        hypothesis.score = min(hypothesis.score, 0.1)
        return hypothesis

    # More than one simultaneous positive check reduces confidence in any
    # single hypothesis (ambiguous evidence), matching the paper's note
    # that overlapping RSRP/SINR/neighbor-cell patterns can confuse causes.
    ambiguity_penalty = 0.15 * max(0, len(positive_checks) - 1)

    layer_evidence = group.by_layer(hypothesis.layer)
    if not layer_evidence and hypothesis.layer.value != "unknown":
        hypothesis.contradicting_evidence.append(
            f"No direct evidence observed at layer '{hypothesis.layer.value}'"
        )
        layer_penalty = 0.2
    else:
        layer_penalty = 0.0

    hypothesis.score = max(0.0, hypothesis.score - ambiguity_penalty - layer_penalty)
    # A hypothesis can only be verified if its score clears the threshold
    # AND there is no unresolved contradicting evidence (e.g. no evidence
    # was observed at its declared layer).
    hypothesis.verified = (
        hypothesis.score >= VERIFICATION_THRESHOLD
        and not hypothesis.contradicting_evidence
    )
    return hypothesis


def verify_hypotheses(
    hypotheses: List[RootCauseHypothesis], group: EvidenceGroup
) -> List[RootCauseHypothesis]:
    """Verify a batch of hypotheses in place, returning the same list."""
    return [verify_hypothesis(h, group) for h in hypotheses]


def select_verified(hypotheses: List[RootCauseHypothesis]) -> List[RootCauseHypothesis]:
    """Return only the hypotheses that passed verification, preserving
    their relative order (callers typically rank before verifying)."""
    return [h for h in hypotheses if h.verified]
