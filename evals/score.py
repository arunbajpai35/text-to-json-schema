"""Field-level scoring of a generated JSON output against a hand-labeled expected output.

Leaves are dotted paths into the expected document. An array is treated as a single leaf —
its value is compared as a multiset, so order doesn't matter but duplicates do.
Missing or differing values count as a miss.
"""
from collections import Counter
from typing import Any, Dict, Iterable, Tuple

_MISSING = object()


def flatten(obj: Any, prefix: str = "") -> Iterable[Tuple[str, Any]]:
    """Yield (path, value) leaves. Stops at arrays and scalars."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                yield from flatten(v, path)
            else:
                yield path, v
    else:
        yield prefix, obj


def _get(obj: Any, path: str) -> Any:
    for part in path.split("."):
        if isinstance(obj, dict) and part in obj:
            obj = obj[part]
        else:
            return _MISSING
    return obj


def _matches(expected: Any, actual: Any) -> bool:
    if actual is _MISSING:
        return False
    if isinstance(expected, list) and isinstance(actual, list):
        return Counter(map(repr, expected)) == Counter(map(repr, actual))
    return expected == actual


def score_case(expected: Dict[str, Any], actual: Dict[str, Any]) -> Dict[str, Any]:
    leaves = list(flatten(expected))
    if not leaves:
        return {"total": 0, "matched": 0, "accuracy": 1.0, "misses": []}

    misses = []
    matched = 0
    for path, exp_value in leaves:
        act_value = _get(actual, path)
        if _matches(exp_value, act_value):
            matched += 1
        else:
            misses.append({
                "path": path,
                "expected": exp_value,
                "actual": None if act_value is _MISSING else act_value,
                "missing": act_value is _MISSING,
            })

    return {
        "total": len(leaves),
        "matched": matched,
        "accuracy": matched / len(leaves),
        "misses": misses,
    }


def aggregate(case_results: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    total = sum(r["total"] for r in case_results)
    matched = sum(r["matched"] for r in case_results)
    return {
        "total": total,
        "matched": matched,
        "accuracy": matched / total if total else 1.0,
    }
