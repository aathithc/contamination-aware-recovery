import argparse
import json
import logging
from pathlib import Path

from care.eval.metrics import compute_metrics

logger = logging.getLogger(__name__)


def run_eval(predictions_path: Path, baseline_path: Path, output_path: Path) -> None:
    with open(predictions_path) as f:
        predictions: dict[str, bool] = json.load(f)
    with open(baseline_path) as f:
        baseline: dict[str, bool] = json.load(f)

    task_ids = list(predictions.keys())
    method_correct = [predictions[t] for t in task_ids]
    baseline_correct = [baseline.get(t, False) for t in task_ids]

    results = compute_metrics(task_ids, baseline_correct, method_correct)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(
            {
                "accuracy": results.accuracy,
                "rescue_rate": results.rescue_rate,
                "harm_rate": results.harm_rate,
                "net_recovery_gain": results.net_recovery_gain,
            },
            f,
            indent=2,
        )
    logger.info("Results written to %s", output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate predictions against baseline")
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--output", default=Path("artifacts/metrics/results.json"), type=Path)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run_eval(args.predictions, args.baseline, args.output)


if __name__ == "__main__":
    main()
