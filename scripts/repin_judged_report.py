#!/usr/bin/env python3
"""Carry frozen human judgments onto a newly gated report and recompute strict pass."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gated", type=Path, required=True)
    parser.add_argument("--judged", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    gated = json.loads(args.gated.read_text())
    judged = json.loads(args.judged.read_text())
    fresh = {row["example_id"]: row for row in gated["results"]}
    old = {row["example_id"]: row for row in judged["results"]}
    if len(fresh) != 200 or set(fresh) != set(old):
        raise SystemExit("reports must cover the same 200 unique examples")

    results = []
    for example_id in sorted(fresh):
        new = fresh[example_id]
        prior = old[example_id]
        for key in ("task_category", "case_type", "expected_action"):
            if new[key] != prior[key]:
                raise SystemExit(f"{example_id}: {key} mismatch")
        row = dict(new)
        row["judge"] = prior["judge"]
        row["overall_pass"] = bool(
            new["deterministic_pass"]
            and all(value["pass"] for value in prior["judge"]["criteria"].values())
        )
        results.append(row)

    summary = dict(gated["summary"])
    summary["judged_count"] = len(results)
    summary["judge_category_pass_rate"] = sum(r["judge"]["category_pass"] for r in results) / len(results)
    summary["judge_all_criteria_pass_rate"] = sum(
        all(v["pass"] for v in r["judge"]["criteria"].values()) for r in results
    ) / len(results)
    summary["overall_pass_rate"] = sum(r["overall_pass"] for r in results) / len(results)
    failures = Counter()
    for row in results:
        for criterion, value in row["judge"]["criteria"].items():
            if not value["pass"]:
                failures[criterion] += 1
    summary["judge_criterion_failures"] = dict(failures.most_common())
    by_category = {}
    for category in sorted({r["task_category"] for r in results}):
        rows = [r for r in results if r["task_category"] == category]
        by_category[category] = {
            "n": len(rows),
            "deterministic_pass": sum(r["deterministic_pass"] for r in rows),
            "overall_pass": sum(r["overall_pass"] for r in rows),
        }
    summary["by_category"] = by_category
    summary["repin_provenance"] = {
        "new_gated_report": str(args.gated),
        "new_gated_report_sha256": sha(args.gated),
        "frozen_judged_report": str(args.judged),
        "frozen_judged_report_sha256": sha(args.judged),
        "method": "new deterministic checks AND all frozen judge criteria; judge criteria unchanged",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"summary": summary, "results": results}, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "gate_version": summary["gate_version"],
        "deterministic": sum(r["deterministic_pass"] for r in results),
        "judge_category": sum(r["judge"]["category_pass"] for r in results),
        "strict": sum(r["overall_pass"] for r in results),
    }, indent=2))


if __name__ == "__main__":
    main()
