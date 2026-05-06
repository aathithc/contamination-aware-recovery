import json
from dataclasses import dataclass
from pathlib import Path

PREFIX_TO_TASK_TYPE: dict[str, str] = {
    "sharded-GSM8K": "math",
    "sharded-totto": "data2text",
    "sharded-spider": "database",
    "sharded-ToolBench": "actions",
}


def infer_task_type(task_id: str) -> str | None:
    """Infer task_type from the task_id prefix using PREFIX_TO_TASK_TYPE mapping."""
    for prefix, task_type in PREFIX_TO_TASK_TYPE.items():
        if task_id.startswith(prefix):
            return task_type
    return None


@dataclass
class LiCTrace:
    task_id: str
    task_type: str
    strategy: str
    success: bool
    turns: list[dict]


def load_lic_traces(
    path: Path | list[Path],
    strategy_filter: str | None = None,
) -> list[LiCTrace]:
    """
    Load LiC traces from one or more JSONL files.

    Parameters
    ----------
    path:
        A single ``Path`` or a list of ``Path`` objects pointing to JSONL files.
    strategy_filter:
        When provided (e.g. ``"none"``), only traces whose ``strategy`` field
        matches this value are returned.

    Returns
    -------
    list[LiCTrace]
    """
    paths: list[Path] = [path] if isinstance(path, Path) else list(path)

    traces: list[LiCTrace] = []
    for p in paths:
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)

                strategy = obj.get("strategy", "")
                if strategy_filter is not None and strategy != strategy_filter:
                    continue

                # task_type: use field if present, else infer from task_id
                task_type = obj.get("task_type") or infer_task_type(obj.get("task_id", "")) or "unknown"

                traces.append(LiCTrace(
                    task_id=obj["task_id"],
                    task_type=task_type,
                    strategy=strategy,
                    success=obj["success"],
                    turns=obj.get("turns", []),
                ))

    return traces
