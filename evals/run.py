"""Run every eval case against the live pipeline and print a field-accuracy report.

Requires azure openai credentials (config.ini or env vars).
Not part of the pytest suite — run on demand:

    python -m evals.run
"""
import argparse
import json
import logging
import sys
from pathlib import Path

from evals.score import aggregate, score_case
from main import process_with_schema
from utils.azure_llm import AzureOpenAIClient
from utils.config_loader import load_config
from utils.schema_processor import SchemaProcessor

CASES_DIR = Path(__file__).parent / "cases"


def _load_case(case_dir: Path):
    return {
        "name": case_dir.name,
        "input": (case_dir / "input.txt").read_text(encoding="utf-8"),
        "schema": json.loads((case_dir / "schema.json").read_text(encoding="utf-8")),
        "expected": json.loads((case_dir / "expected.json").read_text(encoding="utf-8")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run eval cases")
    parser.add_argument("--case", help="Run a single case by directory name")
    parser.add_argument("--out", default="evals/results.json", help="Where to write results")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    config = load_config()
    client = AzureOpenAIClient(config["azure"])
    processor = SchemaProcessor()

    case_dirs = sorted(d for d in CASES_DIR.iterdir() if d.is_dir())
    if args.case:
        case_dirs = [d for d in case_dirs if d.name == args.case]
        if not case_dirs:
            print(f"no case named {args.case}")
            return 1

    results = []
    for case_dir in case_dirs:
        case = _load_case(case_dir)
        actual, _ = process_with_schema(case["input"], case["schema"], client, processor)
        score = score_case(case["expected"], actual)
        score["name"] = case["name"]
        results.append(score)
        print(
            f"{case['name']:30s} {score['matched']:>3}/{score['total']:<3} "
            f"({score['accuracy']:.0%})"
        )

    overall = aggregate(results)
    print("-" * 50)
    print(
        f"{'overall':30s} {overall['matched']:>3}/{overall['total']:<3} "
        f"({overall['accuracy']:.0%})"
    )

    Path(args.out).write_text(
        json.dumps({"cases": results, "overall": overall}, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
