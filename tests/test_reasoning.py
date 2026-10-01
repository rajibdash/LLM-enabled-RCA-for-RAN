from datetime import datetime

from src.common.models import Evidence, EvidenceGroup, EvidenceLayer, EvidenceType
from src.reasoning.engine import DiagnosticThresholds, ReasoningEngine, run_diagnostic_checks


def _group_with_attributes(entity_id="cell-0", **attrs):
    group = EvidenceGroup(entity_id=entity_id)
    group.add(
        Evidence(
            source="test",
            evidence_type=EvidenceType.KPI,
            entity_id=entity_id,
            timestamp=datetime(2026, 1, 1, 0, 0, 0),
            attributes=attrs,
            layer=EvidenceLayer.PHYSICAL,
        )
    )
    return group


def test_run_diagnostic_checks_detects_high_speed():
    group = _group_with_attributes(ue_speed_kmh=50.0)
    checks = run_diagnostic_checks(group)
    assert checks["speed_check"] is True
    assert checks["low_rb_check"] is False


def test_run_diagnostic_checks_detects_low_rb():
    group = _group_with_attributes(scheduled_rbs=100.0)
    checks = run_diagnostic_checks(group, DiagnosticThresholds(low_rb_count=160.0))
    assert checks["low_rb_check"] is True


def test_run_diagnostic_checks_respects_custom_thresholds():
    group = _group_with_attributes(ue_speed_kmh=35.0)
    checks = run_diagnostic_checks(group, DiagnosticThresholds(high_speed_kmh=40.0))
    assert checks["speed_check"] is False


def test_generate_hypotheses_downtilt_case_matches_paper_example():
    # Reproduces the paper's illustrative SEKA-FT sample (ID 92TVA88GDA):
    # all mobility/RB/handover/distance checks are False, so the dominant
    # explanation should be the aggressive downtilt (M3).
    group = _group_with_attributes(
        ue_speed_kmh=38.0,
        scheduled_rbs=177.0,
        handover_count=1,
        ue_distance_km=0.0856,
        mechanical_downtilt_deg=30,
    )

    engine = ReasoningEngine()
    hypotheses = engine.generate_hypotheses(group)
    codes = {h.code for h in hypotheses}

    assert "M3" in codes
    assert "M4" not in codes  # speed_check False
    assert "M1" not in codes  # low_rb_check False
    assert "M2" not in codes  # handover_check False (count below threshold)
    assert "M6" not in codes  # distance_check False


def test_generate_hypotheses_fallback_when_no_check_fires():
    group = _group_with_attributes(unrelated_metric=1)
    engine = ReasoningEngine()
    hypotheses = engine.generate_hypotheses(group)
    assert len(hypotheses) == 1
    assert hypotheses[0].code == "M0"


def test_rank_orders_by_score_then_supporting_evidence():
    engine = ReasoningEngine()
    group = _group_with_attributes(
        ue_speed_kmh=50.0,
        mechanical_downtilt_deg=30,
    )
    hypotheses = engine.generate_hypotheses(group)
    ranked = engine.rank(hypotheses)

    assert len(ranked) >= 2
    # All generated hypotheses start with score 1.0, so ranking falls back
    # to supporting-evidence count (non-increasing order).
    scores_and_support = [(h.score, len(h.supporting_evidence)) for h in ranked]
    assert scores_and_support == sorted(scores_and_support, reverse=True)
