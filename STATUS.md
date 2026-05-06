# CARE Project — Status

## Day 3 Final Summary — 2026-05-06 — DECISION POINT

**Headline:** structural_graph beats baseline by +6.7pp (83.3% vs 76.7%). Pre-registered threshold of ≥10pp NOT MET. Outcome 3 applies — paper must reframe before continuing to other task types.

**Key numbers (30 D2T tasks, strategy=none):**
- Baseline: 76.7% | concat: 63.3% (−13.3pp) | trust_filtered: 70.0% | structural_graph: 83.3% (+6.7pp) | structured_prompt_baseline: 66.7% | Oracle: 86.7%
- structural_graph vs structured_prompt_baseline: +16.7pp (graph adds real value over LLM-only reformatting)
- structural_graph harm rate: 10% vs concat harm rate: 26.7%
- Extraction failures: 0/30. Total API cost: $0.0096.

**Recommended reframe:** Lead with contamination propagation as the core contribution. structural_graph is the only method that improves over baseline; its +16.7pp advantage over structured_prompt_baseline shows the contamination model is doing real work, not just the structured format. See RESULTS_D2T.md for full analysis and three reframing options.

**Stop condition triggered:** Do NOT continue to other task types until researcher decides on framing direction.

## Day 3 Phase 1 — D2T Extraction Fix — DONE (2026-05-06)
Rewrote D2T extraction rules in `src/care/extraction/prompts.py`. Added mandatory D2T detection (triggered by `<table>`/`class="highlighted"` keywords), explicit per-cell structural_record rules, a skip-reference-examples rule for Turn 0, and a correct/incorrect extraction example. Tested on the 5 previously-failing tasks: **5/5 pass** on first attempt (was 2/5 before). Committed `ae9dbf7`.

## Day 3 Phase 2 — Full D2T Pipeline — DONE (2026-05-06)
Ran full pipeline on all 30 D2T strategy=none tasks: extraction (gpt-4o-mini) → contamination propagation → recovery prompts (4 methods) → recovery LLM calls (gpt-4o-mini) → entity-recall scoring. 0 extraction failures. Artifacts saved to `artifacts/extracted_states/`, `artifacts/graphs/`, `artifacts/recovered_prompts/`, `artifacts/predictions/`, `artifacts/metrics/d2t_eval.json`.

## Day 3 Phase 3 — Metrics and RESULTS_D2T.md — DONE (2026-05-06)
Computed per-method accuracy, rescue/harm/net-gain. structural_graph +6.7pp vs baseline, +16.7pp vs structured_prompt_baseline. Pre-registered threshold (≥10pp) not met → Outcome 3. Full analysis in `RESULTS_D2T.md`.

---

# Day 2 Overnight Run Status

## P3 Fix — auto-selector for recovery prompts (2026-05-05, session 2)
Re-ran P3 this session and found 3/5 recovery prompts were empty: the extractor produced `fact` nodes instead of `structural_record` for raw table rows (no `highlighted` attribute set), so `build_structural_graph_prompt` returned "". Switched to `select_and_build` (auto-selector): those 3 tasks fall back to `trust_filtered`. Final method split: structural_graph×2, trust_filtered×3. Logged as Day 3 extraction quality issue: extractor needs a stronger prompt hint for D2T tasks to consistently produce `structural_record` nodes with `highlighted` attribute. All 30 tests still pass. Fix committed and pushed as `70441bb`.

## Final Summary — 2026-05-05
All 6 priorities completed successfully. P1 added the structured_prompt_baseline D2T rewriter with LLM and rule-based fallback paths, and updated the ablation runner. P2 upgraded lic_loader with multi-file loading, strategy filtering, and task_type inference (190 traces loaded across 4 task types). P3 ran the full extraction-contamination-recovery pipeline on 5 failed D2T tasks using gpt-4o-mini with 0% failure rate and diverse recovery method selection. P4 added three well-structured mock fixtures covering database, actions, and data2text scenarios, with all 30 pytest tests passing. P5 pushed all commits to the remote repository successfully via git (gh CLI not required). No priorities were skipped or stopped early.

## Priority 5 — gh install and push — DONE (2026-05-05)
`gh` CLI was not installed on this system (command not found). However, the git remote was already configured for `https://github.com/aathithc/contamination-aware-recovery.git`, and `git push origin main` succeeded without needing `gh auth`. All 4 priority commits (P1–P4) were pushed successfully to the remote main branch.

## Priority 4 — Mock conversation fixtures — DONE (2026-05-05)
Created three fixture JSON files in `tests/fixtures/`: mock_database_001.json (6 nodes, 4 edges with Table/Column/JoinKey structure and BELONGS_TO/REQUIRES edges), mock_actions_001.json (4 nodes, 2 edges demonstrating supersedes contamination propagation on wrong recipient), and mock_summary_001.json (4 nodes, 1 edge showing ignored user constraint). Added corresponding JSONL entries to `data/processed/mock_fixtures.jsonl` covering database, actions, and data2text task types. All 30 pytest tests passed after adding fixtures.

## Priority 3 — Pipeline run on 5 failed D2T tasks — DONE (2026-05-05)
Ran OpenAIExtractor (gpt-4o-mini) on 5 failed data2text tasks (strategy=none) from the Haiku trace file. All 5 extractions succeeded (0 failures, 0% failure rate — well below the 50% stop threshold). Extracted graphs ranged from 19–33 nodes and 4–15 edges per task; no tasks had zero edges. Contamination propagation identified 0–4 contaminated nodes per task. Recovery method selection produced: concat (1 task), structural_graph (2 tasks), trust_filtered (2 tasks). All 5 extracted states and recovery prompts saved to artifacts/. Next: add mock conversation fixtures.

## Priority 2 — lic_loader multi-file support and task_type inference — DONE (2026-05-05)
Updated `src/care/eval/lic_loader.py` to accept a single `Path` or a list of `Path` objects, added `strategy_filter` parameter, and added `PREFIX_TO_TASK_TYPE` + `infer_task_type` for GPT traces that lack the `task_type` field. Validation loaded 190 strategy=none traces across both Haiku and GPT files (math=100, database=30, actions=30, data2text=30). All four task types confirmed present. Next: run extraction pipeline on 5 failed D2T tasks.

## Priority 1 — structured_prompt_baseline D2T rewriter — DONE (2026-05-05)
Created `src/care/recovery/structured_prompt_baseline.py` with `build_structured_prompt` and `build_structured_prompt_from_csg` functions. The module uses gpt-4o-mini when an OpenAI client is supplied and falls back to rule-based section parsing (Table/Highlighted/Context/Instruction) otherwise. Updated `run_ablation.py` to include "structured_prompt_baseline" as a fifth method alongside concat, structural_only, trust_filtered_no_propagation, and full_care; the ablation runner calls `build_structured_prompt_from_csg(clean)` with no LLM client (rule-based fallback). Import test passed.
