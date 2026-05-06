# Contamination-Aware Recovery for Multi-Turn LLM Conversations

Reproducible experiment framework for LiC-style multi-turn conversations.

## Core idea

Parse conversations into typed state units → build a conversation-state graph → propagate contamination from unsupported assistant assumptions through derived claims → recover by generating from uncontaminated or structurally preserved state.

## Design constraints (v1)

- Python + Pydantic schemas, JSONL artifacts, NetworkX graphs
- No Neo4j, no clarification, no tool-output preservation, no CoVe
- LLM used only for extraction/edge proposal, not free-form recovery decisions
- No hand-tuned trust scores — source/type partial order only
- Simple, transparent recovery policy

## Pipeline

```
data/raw/         → run_extract  → artifacts/extracted_states/
                  → run_graph    → artifacts/graphs/
                  → run_recover  → artifacts/recovered_prompts/
                  → run_eval     → artifacts/metrics/
```

## Setup

```bash
pip install -e ".[dev]"
# For LLM extraction:
pip install -e ".[openai]"   # or [anthropic]
```

## Running tests

```bash
pytest
```

## Running the pipeline (mock mode)

```bash
python -m care.experiments.run_extract \
    --input data/processed/mock_math_contamination.jsonl \
    --output-dir artifacts/extracted_states \
    --extractor mock \
    --fixture-dir tests/fixtures

python -m care.experiments.run_graph \
    --extracted-dir artifacts/extracted_states \
    --output-dir artifacts/graphs

python -m care.experiments.run_recover \
    --graph-dir artifacts/graphs \
    --output-dir artifacts/recovered_prompts \
    --method auto
```

## Recovery methods

| Method | Description |
|--------|-------------|
| `concat` | User-only concat baseline |
| `trust_filtered` | Active user/tool + uncontaminated assistant derivations |
| `structural_graph` | Structural retrieval linearization for Data2Text |
| `auto` | Rule-based selector (no task labels) |

## Contamination partial order (high → low trust)

1. Tool output / verified-by-tool
2. User correction
3. User fact / constraint
4. Assistant derivation verified by user or tool
5. Assistant unverified derivation
6. Assistant assumption / answer-candidate without support
