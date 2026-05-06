# CARE Project — Day 2 Overnight Run Status

## Priority 2 — lic_loader multi-file support and task_type inference — DONE (2026-05-05)
Updated `src/care/eval/lic_loader.py` to accept a single `Path` or a list of `Path` objects, added `strategy_filter` parameter, and added `PREFIX_TO_TASK_TYPE` + `infer_task_type` for GPT traces that lack the `task_type` field. Validation loaded 190 strategy=none traces across both Haiku and GPT files (math=100, database=30, actions=30, data2text=30). All four task types confirmed present. Next: run extraction pipeline on 5 failed D2T tasks.

## Priority 1 — structured_prompt_baseline D2T rewriter — DONE (2026-05-05)
Created `src/care/recovery/structured_prompt_baseline.py` with `build_structured_prompt` and `build_structured_prompt_from_csg` functions. The module uses gpt-4o-mini when an OpenAI client is supplied and falls back to rule-based section parsing (Table/Highlighted/Context/Instruction) otherwise. Updated `run_ablation.py` to include "structured_prompt_baseline" as a fifth method alongside concat, structural_only, trust_filtered_no_propagation, and full_care; the ablation runner calls `build_structured_prompt_from_csg(clean)` with no LLM client (rule-based fallback). Import test passed.
