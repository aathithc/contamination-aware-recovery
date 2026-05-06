def compute_oracle_accuracy(
    task_ids: list[str],
    predictions_by_method: dict[str, list[bool]],
) -> tuple[float, dict[str, str]]:
    """
    Oracle: for each task, pick any method that gets it right.
    Returns (oracle_accuracy, per_task_method_selected).
    """
    n = len(task_ids)
    oracle_correct = 0
    oracle_selections: dict[str, str] = {}

    for i, task_id in enumerate(task_ids):
        for method, preds in predictions_by_method.items():
            if preds[i]:
                oracle_correct += 1
                oracle_selections[task_id] = method
                break
        else:
            oracle_selections[task_id] = "none"

    return oracle_correct / n, oracle_selections
