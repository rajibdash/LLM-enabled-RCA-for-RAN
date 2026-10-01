#!/usr/bin/env bash
# Convenience script to run the end-to-end evidence-grounded RCA pipeline.
#
# Usage:
#   ./scripts/run_pipeline.sh path/to/evidence.json [--incident-id ID]
#
# If no evidence file is given, a small bundled sample is used.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SAMPLE_FILE="${REPO_ROOT}/tests/fixtures/sample_incident.json"

INPUT_FILE="${1:-${SAMPLE_FILE}}"
if [ "$#" -gt 0 ]; then
  shift
fi

cd "${REPO_ROOT}"
python3 -m src.api.cli "${INPUT_FILE}" "$@"
