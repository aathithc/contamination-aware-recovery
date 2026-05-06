import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LiCTrace:
    task_id: str
    task_type: str
    strategy: str
    success: bool
    turns: list[dict]


def load_lic_traces(path: Path) -> list[LiCTrace]:
    traces = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            traces.append(LiCTrace(
                task_id=obj["task_id"],
                task_type=obj["task_type"],
                strategy=obj["strategy"],
                success=obj["success"],
                turns=obj["turns"],
            ))
    return traces
