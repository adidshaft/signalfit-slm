#!/usr/bin/env python3
"""Calibrate the current deterministic gates against authored gold answers."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from run_eval import GATE_VERSION, check


def example_files(paths: list[Path]):
    for path in paths:
        files = [path] if path.is_file() else sorted(path.rglob("*.json"))
        for file_path in files:
            try:
                value = json.loads(file_path.read_text())
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if (
                isinstance(value, dict)
                and isinstance(value.get("example_id"), str)
                and isinstance(value.get("target_response", {}).get("text"), str)
            ):
                yield file_path, value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--examples", nargs="+", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    examples: dict[str, tuple[Path, dict]] = {}
    for path, example in example_files(args.examples):
        example_id = example["example_id"]
        if example_id in examples:
            old_path, old = examples[example_id]
            if old != example:
                raise SystemExit(f"conflicting duplicate {example_id}: {old_path} vs {path}")
            continue
        examples[example_id] = (path, example)
    if not examples:
        raise SystemExit("no authored examples found")

    checked = 0
    failures = []
    gold_lines = []
    for example_id in sorted(examples):
        path, example = examples[example_id]
        answer = example["target_response"]["text"]
        checks = check(example, answer)
        failed = {name: result for name, result in checks.items() if not result["pass"]}
        checked += 1
        if failed:
            failures.append({"example_id": example_id, "source": str(path), "failures": failed})
        gold_lines.append(json.dumps({"example_id": example_id, "answer": answer}, ensure_ascii=False))

    payload = {
        "gate_version": GATE_VERSION,
        "count": checked,
        "passed": checked - len(failures),
        "failures": failures,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    report = args.out / "calibration_report.json"
    report.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    gold = args.out / "gold_generations.jsonl"
    gold.write_text("\n".join(gold_lines) + "\n")
    manifest = {
        "gate_version": GATE_VERSION,
        "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
        "gold_sha256": hashlib.sha256(gold.read_bytes()).hexdigest(),
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"{GATE_VERSION}: {checked - len(failures)}/{checked} golds pass")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
