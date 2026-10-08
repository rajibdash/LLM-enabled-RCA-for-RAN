# LLM-enabled-RCA-for-RAN

Structured, evidence-grounded LLM-enabled Root Cause Analysis (RCA) for telecom
RAN/5G/6G networks — a reference implementation inspired by the paper *"Large
Language Models (LLMs) for Telecom Root Cause Analysis (RCA): A Structured
Reasoning Framework for Evidence-Grounded Diagnosis"* (accepted by IEEE
Wireless Communications Magazine).

> **Core message:** LLMs are valuable for telecom RCA only when embedded in a
> structured, evidence-grounded reasoning pipeline — not as a free-form
> chatbot. See [`AI-ML-or-LLM-RCA.md`](AI-ML-or-LLM-RCA.md) for the full
> paper content (abstract, motivation, challenges, the SEKA-FT framework,
> experimental results on TeleLogs/TelecomTS, and design details).

## Repository Structure

```text
LLM-enabled-RCA-for-RAN/
├── README.md
├── AI-ML-or-LLM-RCA.md       # Full detailed paper content & framework design
├── AI:ML or LLM RCA.pdf      # Source paper (primary reference)
├── LICENSE
├── requirements.txt
├── pyproject.toml
├── docs/
│   ├── architecture.md       # Module-level architecture
│   └── rca-workflow.md       # End-to-end runtime workflow
├── src/
│   ├── common/               # Shared data models (Evidence, RootCauseHypothesis, ...)
│   ├── ingestion/            # Normalizes heterogeneous telemetry
│   ├── correlation/          # Cross-layer / cross-time evidence correlation
│   ├── retrieval/            # Knowledge base retrieval (RAG-style grounding)
│   ├── prompts/              # Prompt templates / explanation builders
│   ├── reasoning/            # Candidate root-cause generation & ranking
│   ├── validation/           # Evidence-grounded hypothesis verification
│   └── api/                  # Pipeline entry point & CLI
├── models/
│   └── llm-config/           # Example LLM configuration
├── notebooks/
│   └── experiments.ipynb     # Lightweight experimentation notebook
├── scripts/
│   └── run_pipeline.sh       # Run the pipeline from the command line
└── tests/
    ├── fixtures/             # Sample evidence data
    ├── test_ingestion.py     # Data ingestion
    ├── test_correlation.py   # co-relation among those evidence
    ├── test_reasoning.py     # Root cause reasoning
    ├── test_validation.py    # Evidence grounded verifications
    └── test_pipeline.py      # End-to-end smoke test
```

## Quick Start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run the sample pipeline
./scripts/run_pipeline.sh

# Or run against your own evidence file
./scripts/run_pipeline.sh path/to/evidence.json --incident-id my-incident

# Run the test suite
pip install pytest
pytest
```

Programmatic usage:

```python
from src.api.cli import run_pipeline

result = run_pipeline(raw_records, incident_id="incident-123")
print(result.explain())
```

## Documentation

- [`AI-ML-or-LLM-RCA.md`](AI-ML-or-LLM-RCA.md) — full paper content: abstract,
  motivation, challenges, LLM-enabled technique progression (CoT → RAG →
  Agentic → RLVR), the SEKA-FT framework, TeleLogs/TelecomTS experimental
  results, architecture & reasoning-flow diagrams, and conclusion.
- [`docs/architecture.md`](docs/architecture.md) — module-by-module
  architecture of this repository's reference implementation.
- [`docs/rca-workflow.md`](docs/rca-workflow.md) — the nine-stage end-to-end
  RCA workflow and how it maps onto the code.

## License

See [`LICENSE`](LICENSE).
