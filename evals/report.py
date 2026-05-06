"""Render the eval results into the README between the BEGIN/END markers.

    python -m evals.report

Reads evals/results.json (whatever evals/run.py last wrote) and rewrites the
section in README.md so the published numbers don't drift from reality.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "evals" / "results.json"
README = ROOT / "README.md"

BEGIN = "<!-- BEGIN_EVAL_TABLE -->"
END = "<!-- END_EVAL_TABLE -->"


def render(data: dict) -> str:
    cases = data["cases"]
    overall = data["overall"]
    width = max(len(c["name"]) for c in cases)
    lines = [
        f"| {'case'.ljust(width)} | score    |",
        f"| {'-' * width} | -------- |",
    ]
    for c in cases:
        lines.append(f"| {c['name'].ljust(width)} | {c['matched']}/{c['total']:<6} |")
    lines.append(
        f"| **{'overall'.ljust(width - 4)}** | **{overall['matched']}/{overall['total']} "
        f"({overall['accuracy']:.0%})** |"
    )
    return "\n".join(lines)


def main() -> int:
    if not RESULTS.exists():
        print(f"no results at {RESULTS} — run `python -m evals.run` first", file=sys.stderr)
        return 1
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    table = render(data)

    body = README.read_text(encoding="utf-8")
    if BEGIN not in body or END not in body:
        print(f"README is missing the {BEGIN} / {END} markers", file=sys.stderr)
        return 1
    head, _, tail = body.partition(BEGIN)
    _, _, tail = tail.partition(END)
    new = f"{head}{BEGIN}\n{table}\n{END}{tail}"
    README.write_text(new, encoding="utf-8")
    print(f"updated {README} with {len(data['cases'])} cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
