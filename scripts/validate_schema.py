#!/usr/bin/env python3
"""Validate SignalFit training examples against the JSON Schemas + grounding gate.

Usage:
    .venv/bin/python scripts/validate_schema.py <file-or-dir> [...]

Checks per example:
  1. training_example.schema.json validity (context $ref resolved locally).
  2. assistant_context.schema.json validity of example["context"].
  3. Deterministic grounding gate: every number+unit token in
     target_response.text must match an allowed_numbers entry within +/-1.0
     (same rule as prompts/synthetic_data_critic.md and Atria's fabricationFlags).
  4. missing_fields consistency: every listed missing field that maps to a
     required leaf is actually null in the context.

Exit code 0 iff every example passes.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCHEMAS = REPO / "schemas"

NUM_UNIT = re.compile(
    r"([0-9]+(?:\.[0-9]+)?)\s?(%|bpm|ms|kcal|steps?|kg|lbs?|h(?:ours?)?|min(?:utes?)?|drinks?)",
    re.IGNORECASE,
)

# missing_fields name -> path into context for the nullability cross-check
MISSING_FIELD_PATHS = {
    "recovery_score": ("today", "recovery_score"),
    "hrv_ms": ("today", "hrv_ms"),
    "resting_heart_rate_bpm": ("today", "resting_heart_rate_bpm"),
    "respiratory_rate_bpm": ("today", "respiratory_rate_bpm"),
    "activity_strain": ("today", "activity", "activity_strain"),
    "sleep_duration_minutes": ("today", "sleep", "duration_minutes"),
    "baseline_30d": ("baselines", "baseline_30d"),
    "trends.window_7d": ("trends", "window_7d"),
}


def load_validators():
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
    except ImportError:
        sys.exit("jsonschema not installed. Run: python3 -m venv .venv && .venv/bin/pip install jsonschema")

    ctx_schema = json.loads((SCHEMAS / "assistant_context.schema.json").read_text())
    tr_schema = json.loads((SCHEMAS / "training_example.schema.json").read_text())
    registry = Registry().with_resources(
        [
            (ctx_schema["$id"], Resource.from_contents(ctx_schema)),
            (tr_schema["$id"], Resource.from_contents(tr_schema)),
        ]
    )
    return (
        Draft202012Validator(tr_schema, registry=registry),
        Draft202012Validator(ctx_schema, registry=registry),
    )


def dig(obj, path):
    for key in path:
        if not isinstance(obj, dict) or key not in obj:
            return None
        obj = obj[key]
    return obj


def grounding_errors(example: dict) -> list[str]:
    allowed = [a["value"] for a in example["context"].get("allowed_numbers", [])]
    errors = []
    for match in NUM_UNIT.finditer(example["target_response"]["text"]):
        value = float(match.group(1))
        if not any(abs(v - value) <= 1.0 for v in allowed):
            errors.append(f"ungrounded number token {match.group(0)!r}")
    return errors


def missing_field_errors(example: dict) -> list[str]:
    ctx = example["context"]
    errors = []
    for name in ctx.get("data_quality", {}).get("missing_fields", []):
        path = MISSING_FIELD_PATHS.get(name)
        if path is not None and dig(ctx, path) is not None:
            errors.append(f"missing_fields lists {name!r} but context value is not null")
    return errors


def iter_example_files(args: list[str]):
    for arg in args:
        p = Path(arg)
        if p.is_dir():
            yield from sorted(p.rglob("*.json"))
        elif p.suffix == ".json":
            yield p


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    tr_validator, ctx_validator = load_validators()
    failed = passed = 0
    for path in iter_example_files(argv):
        example = json.loads(path.read_text())
        errors = [
            f"schema: {'/'.join(map(str, e.path))}: {e.message}"
            for v, doc in ((tr_validator, example), (ctx_validator, example.get("context", {})))
            for e in v.iter_errors(doc)
        ]
        errors += grounding_errors(example)
        errors += missing_field_errors(example)
        if errors:
            failed += 1
            print(f"FAIL {path}")
            for err in errors[:10]:
                print(f"     {err}")
        else:
            passed += 1
    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
