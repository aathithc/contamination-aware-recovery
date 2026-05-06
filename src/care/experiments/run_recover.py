import argparse
import logging
from pathlib import Path

from care.io_utils import read_json, write_json
from care.schemas import ConversationStateGraph
from care.recovery.selector import select_and_build
from care.recovery.concat import build_concat_prompt
from care.recovery.trust_filtered import build_trust_filtered_prompt
from care.recovery.structural_graph import build_structural_graph_prompt

logger = logging.getLogger(__name__)

METHOD_MAP = {
    "auto": select_and_build,
    "concat": build_concat_prompt,
    "trust_filtered": build_trust_filtered_prompt,
    "structural_graph": build_structural_graph_prompt,
}


def run_recover(graph_dir: Path, output_dir: Path, method: str = "auto") -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    builder = METHOD_MAP[method]

    for json_path in sorted(graph_dir.glob("*.json")):
        if json_path.parent.name == "reports":
            continue
        csg = read_json(json_path, ConversationStateGraph)
        prompt = builder(csg)
        write_json(prompt, output_dir / json_path.name)
        logger.info("%s → method=%s", json_path.stem, prompt.method)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run recovery prompt generation")
    parser.add_argument("--graph-dir", default=Path("artifacts/graphs"), type=Path)
    parser.add_argument("--output-dir", default=Path("artifacts/recovered_prompts"), type=Path)
    parser.add_argument("--method", default="auto", choices=list(METHOD_MAP))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run_recover(args.graph_dir, args.output_dir, args.method)


if __name__ == "__main__":
    main()
