import json
from pathlib import Path
from typing import Iterator, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def write_jsonl(records: list[BaseModel], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for record in records:
            f.write(record.model_dump_json() + "\n")


def read_jsonl(path: Path, model: type[T]) -> list[T]:
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(model.model_validate_json(line))
    return records


def iter_jsonl(path: Path, model: type[T]) -> Iterator[T]:
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                yield model.model_validate_json(line)


def write_json(record: BaseModel, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(record.model_dump_json(indent=2))


def read_json(path: Path, model: type[T]) -> T:
    with open(path) as f:
        return model.model_validate_json(f.read())


def append_jsonl(record: BaseModel, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(record.model_dump_json() + "\n")
