from datetime import datetime

from src.common.models import (
    Evidence,
    EvidenceGroup,
    EvidenceLayer,
    EvidenceType,
    RootCauseHypothesis,
)
from src.validation.validator import (
    VERIFICATION_THRESHOLD,
    select_verified,
    verify_hypothesis,
)


def _group_with_layer_evidence(layer):
    group = EvidenceGroup(entity_id="cell-0")
    group.add(
        Evidence(
            source="test",
            evidence_type=EvidenceType.KPI,
            entity_id="cell-0",
            timestamp=datetime(2026, 1, 1, 0, 0, 0),
            layer=layer,
        )
    )
    return group


def test_verify_hypothesis_passes_with_single_supporting_check_and_layer_evidence():
    group = _group_with_layer_evidence(EvidenceLayer.PHYSICAL)
    hypothesis = RootCauseHypothesis(
        code="M3",
        description="Aggressive downtilt",
        layer=EvidenceLayer.PHYSICAL,
        score=1.0,
        checks={"downtilt_check": True, "speed_check": False},
    )

    verified = verify_hypothesis(hypothesis, group)

    assert verified.verified is True
    assert verified.score >= VERIFICATION_THRESHOLD
    assert not verified.contradicting_evidence


def test_verify_hypothesis_fails_without_backing_check():
    group = _group_with_layer_evidence(EvidenceLayer.PHYSICAL)
    hypothesis = RootCauseHypothesis(
        code="M3",
        description="Aggressive downtilt",
        layer=EvidenceLayer.PHYSICAL,
        score=1.0,
        checks={"downtilt_check": False},
    )

    verified = verify_hypothesis(hypothesis, group)

    assert verified.verified is False
    assert verified.score <= 0.1
    assert verified.contradicting_evidence


def test_verify_hypothesis_penalizes_ambiguous_multi_check_evidence():
    group = _group_with_layer_evidence(EvidenceLayer.PHYSICAL)
    unambiguous = RootCauseHypothesis(
        code="M3",
        description="Aggressive downtilt",
        layer=EvidenceLayer.PHYSICAL,
        score=1.0,
        checks={"downtilt_check": True},
    )
    ambiguous = RootCauseHypothesis(
        code="M3",
        description="Aggressive downtilt",
        layer=EvidenceLayer.PHYSICAL,
        score=1.0,
        checks={"downtilt_check": True, "speed_check": True, "handover_check": True},
    )

    verified_unambiguous = verify_hypothesis(unambiguous, group)
    verified_ambiguous = verify_hypothesis(ambiguous, group)

    assert verified_unambiguous.score > verified_ambiguous.score


def test_verify_hypothesis_flags_missing_layer_evidence():
    group = _group_with_layer_evidence(EvidenceLayer.PHYSICAL)
    hypothesis = RootCauseHypothesis(
        code="M8",
        description="Transport bottleneck",
        layer=EvidenceLayer.TRANSPORT,  # no transport evidence in this group
        score=1.0,
        checks={"transport_check": True},
    )

    verified = verify_hypothesis(hypothesis, group)

    assert any("transport" in msg for msg in verified.contradicting_evidence)


def test_select_verified_filters_unverified_hypotheses():
    group = _group_with_layer_evidence(EvidenceLayer.PHYSICAL)
    good = RootCauseHypothesis(
        code="M3", description="good", layer=EvidenceLayer.PHYSICAL, score=1.0,
        checks={"downtilt_check": True},
    )
    bad = RootCauseHypothesis(
        code="M4", description="bad", layer=EvidenceLayer.PHYSICAL, score=1.0,
        checks={"speed_check": False},
    )
    verify_hypothesis(good, group)
    verify_hypothesis(bad, group)

    verified_only = select_verified([good, bad])

    assert verified_only == [good]
