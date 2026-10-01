"""End-to-end pipeline entry point and CLI.

Wires together ingestion -> correlation -> reasoning -> validation into
the full RCA workflow described in Section 8 of AI-ML-or-LLM-RCA.md, and
exposes it as both a importable function (``run_pipeline``) and a small
command-line interface.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List

from src.common.models import RCAResult
from src.correlation.correlator import correlate_by_entity, merge_groups
from src.ingestion.normalizer import normalize_records
from src.reasoning.engine import ReasoningEngine
from src.validation.validator import verify_hypotheses


def run_pipeline(
    raw_records: List[Dict[str, Any]],
    incident_id: str = "incident-unknown",
    engine: ReasoningEngine | None = None,
) -> RCAResult:
    """Run the full evidence-grounded RCA pipeline over raw telemetry
    records for a single incident and return a ranked, verified result.
    """
    engine = engine or ReasoningEngine()

    evidences = normalize_records(raw_records)
    groups_by_entity = correlate_by_entity(evidences)

    all_groups = [group for groups in groups_by_entity.values() for group in groups]
    if not all_groups:
        return RCAResult(incident_id=incident_id, ranked_hypotheses=[])

    merged_group = merge_groups(all_groups)

    hypotheses = engine.generate_hypotheses(merged_group)
    hypotheses = verify_hypotheses(hypotheses, merged_group)
    ranked = engine.rank(hypotheses)

    return RCAResult(incident_id=incident_id, ranked_hypotheses=ranked)


def _load_records(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        data = data.get("records", [])
    return data


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="rca-pipeline",
        description="Run the evidence-grounded telecom RCA pipeline over a JSON evidence file.",
    )
    parser.add_argument(
        "input",
        help="Path to a JSON file containing a list of raw telemetry records "
        "(or an object with a 'records' key).",
    )
    parser.add_argument(
        "--incident-id",
        default="incident-cli",
        help="Identifier to attach to the resulting RCAResult.",
    )
    args = parser.parse_args(argv)

    records = _load_records(args.input)
    result = run_pipeline(records, incident_id=args.incident_id)
    print(result.explain())
    return 0


if __name__ == "__main__":
    sys.exit(main())
