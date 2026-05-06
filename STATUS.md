# CARE Project — Day 2 Overnight Run Status

## Priority 4 — Mock conversation fixtures — DONE (2026-05-05)
Created three fixture JSON files in `tests/fixtures/`: mock_database_001.json (6 nodes, 4 edges with Table/Column/JoinKey structure and BELONGS_TO/REQUIRES edges), mock_actions_001.json (4 nodes, 2 edges demonstrating supersedes contamination propagation on wrong recipient), and mock_summary_001.json (4 nodes, 1 edge showing ignored user constraint). Added corresponding JSONL entries to `data/processed/mock_fixtures.jsonl` covering database, actions, and data2text task types. All 30 pytest tests passed after adding fixtures.

## Priority 3 — Pipeline run on 5 failed D2T tasks — DONE (2026-05-05)
Ran OpenAIExtractor (gpt-4o-mini) on 5 failed data2text tasks (strategy=none) from the Haiku trace file. All 5 extractions succeeded (0 failures, 0% failure rate — well below the 50% stop threshold). Extracted graphs ranged from 19–33 nodes and 4–15 edges per task; no tasks had zero edges. Contamination propagation identified 0–4 contaminated nodes per task. Recovery method selection produced: concat (1 task), structural_graph (2 tasks), trust_filtered (2 tasks). All 5 extracted states and recovery prompts saved to artifacts/. Next: add mock conversation fixtures.

## Priority 2 — lic_loader multi-file support and task_type inference — DONE (2026-05-05)
Updated `src/care/eval/lic_loader.py` to accept a single `Path` or a list of `Path` objects, added `strategy_filter` parameter, and added `PREFIX_TO_TASK_TYPE` + `infer_task_type` for GPT traces that lack the `task_type` field. Validation loaded 190 strategy=none traces across both Haiku and GPT files (math=100, database=30, actions=30, data2text=30). All four task types confirmed present. Next: run extraction pipeline on 5 failed D2T tasks.

## Priority 1 — structured_prompt_baseline D2T rewriter — DONE (2026-05-05)
Created `src/care/recovery/structured_prompt_baseline.py` with `build_structured_prompt` and `build_structured_prompt_from_csg` functions. The module uses gpt-4o-mini when an OpenAI client is supplied and falls back to rule-based section parsing (Table/Highlighted/Context/Instruction) otherwise. Updated `run_ablation.py` to include "structured_prompt_baseline" as a fifth method alongside concat, structural_only, trust_filtered_no_propagation, and full_care; the ablation runner calls `build_structured_prompt_from_csg(clean)` with no LLM client (rule-based fallback). Import test passed.
