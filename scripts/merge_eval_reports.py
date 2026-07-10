#!/usr/bin/env python3
"""Merge non-overlapping eval reports from append-only suite slices.

This is for a sanctioned eval-suite expansion: old case results stay immutable
and newly generated/judged slice reports are merged into one comparable report.
All inputs must carry the same gate and rubric stamps and may not overlap IDs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load(path: Path) -> dict:
    report = json.loads(path.read_text())
    if not isinstance(report.get("summary"), dict) or not isinstance(report.get("results"), list):
        sys.exit(f"not an eval report: {path}")
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    reports = [load(Path(raw)) for raw in args.reports]
    stamps = {(r["summary"].get("gate_version"), r["summary"].get("rubric_version")) for r in reports}
    if len(stamps) != 1:
        sys.exit(f"cannot merge mismatched report versions: {sorted(stamps)}")

    results: list[dict] = []
    ids: set[str] = set()
    for report in reports:
        for result in report["results"]:
            example_id = result["example_id"]
            if example_id in ids:
                sys.exit(f"duplicate example_id across reports: {example_id}")
            ids.add(example_id)
            results.append(result)
    results.sort(key=lambda r: r["example_id"])

    gate_version, rubric_version = next(iter(stamps))
    n = len(results)
    by_gate: dict[str, dict[str, int]] = {}
    by_category: dict[str, dict[str, int]] = {}
    for result in results:
        for gate, check in result["checks"].items():
            item = by_gate.setdefault(gate, {"n": 0, "pass": 0})
            item["n"] += 1
            item["pass"] += bool(check["pass"])
        category = by_category.setdefault(
            result["task_category"], {"n": 0, "deterministic_pass": 0, "overall_pass": 0})
        category["n"] += 1
        category["deterministic_pass"] += bool(result["deterministic_pass"])
        category["overall_pass"] += bool(result.get("overall_pass", False))

    judged = [r for r in results if r.get("judge") is not None]
    any_judged = bool(judged)
    if any_judged and len(judged) != n:
        sys.exit(f"cannot merge partly judged report: {len(judged)}/{n} have verdicts")
    summary: dict[str, object] = {
        "gate_version": gate_version,
        "rubric_version": rubric_version,
        "count": n,
        "deterministic_pass_rate": round(sum(bool(r["deterministic_pass"]) for r in results) / n, 3) if n else None,
        "grounding_pass_rate": round(sum(bool(r["checks"]["x1_grounding"]["pass"]) for r in results) / n, 3) if n else None,
        "by_gate": by_gate,
        "by_category": by_category,
    }
    if any_judged:
        criterion_fails: dict[str, int] = {}
        for result in judged:
            for criterion_id, criterion in result["judge"]["criteria"].items():
                if not criterion["pass"]:
                    criterion_fails[criterion_id] = criterion_fails.get(criterion_id, 0) + 1
        summary.update({
            "judged_count": n,
            "judge_category_pass_rate": round(sum(r["judge"]["category_pass"] for r in judged) / n, 3),
            "judge_all_criteria_pass_rate": round(sum(r["judge"]["criteria_pass"] for r in judged) / n, 3),
            "overall_pass_rate": round(sum(bool(r["overall_pass"]) for r in results) / n, 3),
            "judge_criterion_failures": dict(sorted(criterion_fails.items(), key=lambda item: -item[1])),
        })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"merged {len(reports)} reports / {n} examples -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
