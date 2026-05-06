import argparse
import logging
from pathlib import Path

from care.eval.lic_loader import load_lic_traces
from care.extraction.llm_extractor import MockExtractor, OpenAIExtractor, AnthropicExtractor
from care.io_utils import write_json

logger = logging.getLogger(__name__)


def run_extract(
    input_path: Path,
    output_dir: Path,
    extractor_type: str = "mock",
    fixture_dir: Path | None = None,
    model: str | None = None,
) -> None:
    traces = load_lic_traces(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    if extractor_type == "mock":
        extractor = MockExtractor(fixture_dir or Path("tests/fixtures"))
    elif extractor_type == "openai":
        extractor = OpenAIExtractor(model=model or "gpt-4o")
    elif extractor_type == "anthropic":
        extractor = AnthropicExtractor(model=model or "claude-opus-4-7")
    else:
        raise ValueError(f"Unknown extractor type: {extractor_type!r}")

    for trace in traces:
        csg = extractor.extract_state(trace.task_id, trace.turns)
        write_json(csg, output_dir / f"{trace.task_id}.json")
        logger.info("Extracted %s → %s/%s.json", trace.task_id, output_dir, trace.task_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run state extraction on LiC traces")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", default=Path("artifacts/extracted_states"), type=Path)
    parser.add_argument("--extractor", default="mock", choices=["mock", "openai", "anthropic"])
    parser.add_argument("--fixture-dir", type=Path)
    parser.add_argument("--model", type=str)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run_extract(
        input_path=args.input,
        output_dir=args.output_dir,
        extractor_type=args.extractor,
        fixture_dir=args.fixture_dir,
        model=args.model,
    )


if __name__ == "__main__":
    main()
