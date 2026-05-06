import argparse
import json
import logging
from pathlib import Path

from care.io_utils import read_json, write_json
from care.schemas import ConversationStateGraph
from care.graph.contamination import propagate_contamination

logger = logging.getLogger(__name__)


def run_graph(extracted_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir = output_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    for json_path in sorted(extracted_dir.glob("*.json")):
        csg = read_json(json_path, ConversationStateGraph)
        updated_csg, report = propagate_contamination(csg)

        write_json(updated_csg, output_dir / json_path.name)

        with open(report_dir / json_path.name, "w") as f:
            json.dump(
                {
                    "contaminated_ids": report.contaminated_ids,
                    "inactive_ids": report.inactive_ids,
                    "reasons": report.reasons,
                },
                f,
                indent=2,
            )

        logger.info(
            "%s: %d contaminated, %d inactive",
            json_path.stem,
            len(report.contaminated_ids),
            len(report.inactive_ids),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run contamination propagation")
    parser.add_argument("--extracted-dir", default=Path("artifacts/extracted_states"), type=Path)
    parser.add_argument("--output-dir", default=Path("artifacts/graphs"), type=Path)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run_graph(args.extracted_dir, args.output_dir)


if __name__ == "__main__":
    main()
