from dataclasses import dataclass


@dataclass
class EvalResults:
    accuracy: float
    rescue_rate: float
    harm_rate: float
    net_recovery_gain: float
    oracle_regret: float | None = None


def compute_metrics(
    task_ids: list[str],
    baseline_correct: list[bool],
    method_correct: list[bool],
    oracle_accuracy: float | None = None,
) -> EvalResults:
    n = len(task_ids)
    assert len(baseline_correct) == n, "baseline_correct length mismatch"
    assert len(method_correct) == n, "method_correct length mismatch"

    accuracy = sum(method_correct) / n
    rescue_rate = sum(1 for b, m in zip(baseline_correct, method_correct) if not b and m) / n
    harm_rate = sum(1 for b, m in zip(baseline_correct, method_correct) if b and not m) / n
    net_recovery_gain = rescue_rate - harm_rate
    oracle_regret = (oracle_accuracy - accuracy) if oracle_accuracy is not None else None

    return EvalResults(
        accuracy=accuracy,
        rescue_rate=rescue_rate,
        harm_rate=harm_rate,
        net_recovery_gain=net_recovery_gain,
        oracle_regret=oracle_regret,
    )
