"""
Ablation runner: generates recovery prompts for all method variants, saves them
to artifacts/recovered_prompts/{method}/, then computes metrics from supplied labels.

Methods compared:
  concat                        — user-only baseline, no contamination
  structural_only               — structural_graph recovery, no contamination propagation
  trust_filtered_no_propagation — trust_filtered recovery, no contamination propagation
  full_care                     — auto selector after full contamination propagation
  oracle                        — upper-bound from best per-task method
"""

import argparse
import json
import logging
from pathlib import Path

from care.io_utils import read_json, write_json
from care.schemas import ConversationStateGraph, NodeStatus
from care.graph.contamination import propagate_contamination
from care.recovery.concat import build_concat_prompt
from care.recovery.trust_filtered import build_trust_filtered_prompt
from care.recovery.structural_graph import build_structural_graph_prompt
from care.recovery.selector import select_and_build
from care.recovery.structured_prompt_baseline import build_structured_prompt_from_csg
from care.eval.metrics import compute_metrics
from care.eval.oracle import compute_oracle_accuracy

logger = logging.getLogger(__name__)


def _reset_statuses(csg: ConversationStateGraph) -> ConversationStateGraph:
    nodes = [n.model_copy(update={"status": NodeStatus.active}) for n in csg.nodes]
    return ConversationStateGraph(
        conversation_id=csg.conversation_id,
        nodes=nodes,
        edges=csg.edges,
        attributes=csg.attributes,
    )


def run_ablation(
    extracted_dir: Path,
    graph_dir: Path,
    output_dir: Path,
    success_labels: dict[str, bool],
) -> dict:
    task_ids = list(success_labels.keys())
    predictions_by_method: dict[str, list[bool]] = {
        m: [] for m in ["concat", "structural_only", "trust_filtered_no_propagation", "full_care", "structured_prompt_baseline"]
    }

    for task_id in task_ids:
        # Load un-propagated graph (from extracted_states)
        raw_path = extracted_dir / f"{task_id}.json"
        # Load propagated graph (from graphs dir)
        prop_path = graph_dir / f"{task_id}.json"

        if not raw_path.exists() and not prop_path.exists():
            logger.warning("No graph found for %s, skipping", task_id)
            for m in predictions_by_method:
                predictions_by_method[m].append(False)
            continue

        raw_csg = read_json(raw_path, ConversationStateGraph) if raw_path.exists() else None
        prop_csg = read_json(prop_path, ConversationStateGraph) if prop_path.exists() else None

        clean = _reset_statuses(raw_csg) if raw_csg else _reset_statuses(prop_csg)
        propagated = prop_csg if prop_csg else propagate_contamination(clean)[0]

        prompts = {
            "concat": build_concat_prompt(clean),
            "structural_only": build_structural_graph_prompt(clean),
            "trust_filtered_no_propagation": build_trust_filtered_prompt(clean),
            "full_care": select_and_build(propagated),
            "structured_prompt_baseline": build_structured_prompt_from_csg(clean),
        }

        for method_name, prompt in prompts.items():
            method_out = output_dir / method_name
            method_out.mkdir(parents=True, exist_ok=True)
            write_json(prompt, method_out / f"{task_id}.json")
            # Placeholder: actual correctness requires running the recovered prompt through an LLM
            predictions_by_method[method_name].append(success_labels.get(task_id, False))

    baseline_correct = [success_labels.get(t, False) for t in task_ids]
    results: dict = {}

    oracle_acc, oracle_sels = compute_oracle_accuracy(task_ids, predictions_by_method)
    results["oracle"] = {"accuracy": oracle_acc, "selections": oracle_sels}

    for method_name, preds in predictions_by_method.items():
        r = compute_metrics(task_ids, baseline_correct, preds, oracle_accuracy=oracle_acc)
        results[method_name] = {
            "accuracy": r.accuracy,
            "rescue_rate": r.rescue_rate,
            "harm_rate": r.harm_rate,
            "net_recovery_gain": r.net_recovery_gain,
            "oracle_regret": r.oracle_regret,
        }

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ablation study")
    parser.add_argument("--extracted-dir", default=Path("artifacts/extracted_states"), type=Path)
    parser.add_argument("--graph-dir", default=Path("artifacts/graphs"), type=Path)
    parser.add_argument("--output-dir", default=Path("artifacts/recovered_prompts"), type=Path)
    parser.add_argument("--labels", required=True, type=Path, help="JSON {task_id: bool}")
    parser.add_argument("--metrics-out", default=Path("artifacts/metrics/ablation.json"), type=Path)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    with open(args.labels) as f:
        labels: dict[str, bool] = json.load(f)

    results = run_ablation(args.extracted_dir, args.graph_dir, args.output_dir, labels)

    args.metrics_out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.metrics_out, "w") as f:
        json.dump(results, f, indent=2)
    logger.info("Ablation results → %s", args.metrics_out)


if __name__ == "__main__":
    main()
