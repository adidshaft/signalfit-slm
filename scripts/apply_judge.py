#!/usr/bin/env python3
"""Merge LLM-judge verdicts into an eval report -> judged_report.json.

Usage:
    .venv/bin/python scripts/apply_judge.py \
        --report data/ft_v2/eval_report_gates3/eval_report.json \
        --verdicts data/ft_v2/eval_report_gates3/judge_verdicts.jsonl \
        --out data/ft_v2/eval_report_gates3/judged_report.json

Verdict line format (one per example, produced by a judge working through
judge_bundle.jsonl — a frontier model, an agent, or a human):
    {"example_id": str,
     "criteria": {"<id>": {"pass": bool, "reason": str}, ...},
     "category_pass": bool,
     "judge": str}          # who judged, e.g. "agent-fable-5-agent"

An example's overall_pass = deterministic_pass AND category_pass. The judged
report keeps the gate/rubric version stamps from the input report; regression
checks (scripts/check_regression.py) refuse to compare across versions.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--allow-missing", action="store_true",
                    help="tolerate examples without a verdict (default: error)")
    args = ap.parse_args()

    report = json.loads(Path(args.report).read_text())
    verdicts: dict[str, dict] = {}
    for line in Path(args.verdicts).read_text().splitlines():
        if not line.strip():
            continue
        v = json.loads(line)
        if v["example_id"] in verdicts:
            sys.exit(f"duplicate verdict for {v['example_id']}")
        verdicts[v["example_id"]] = v

    known = {r["example_id"] for r in report["results"]}
    unknown = set(verdicts) - known
    if unknown:
        sys.exit(f"verdicts for examples not in report: {sorted(unknown)}")
    missing = known - set(verdicts)
    if missing and not args.allow_missing:
        sys.exit(f"{len(missing)} examples lack a verdict (use --allow-missing to score anyway): "
                 f"{sorted(missing)[:5]}{'...' if len(missing) > 5 else ''}")

    results = []
    for r in report["results"]:
        v = verdicts.get(r["example_id"])
        merged = dict(r)
        # criteria_pass is the strict bar (rubric roll-up: cross_cutting AND
        # category): an answer with a judge-confirmed false qualitative claim
        # (X1) fails overall even when its category criteria all pass.
        merged["judge"] = None if v is None else {
            "judge": v.get("judge"),
            "category_pass": v["category_pass"],
            "criteria_pass": all(c["pass"] for c in v["criteria"].values()),
            "criteria": v["criteria"],
        }
        merged["overall_pass"] = bool(
            r["deterministic_pass"] and v and v["category_pass"]
            and merged["judge"]["criteria_pass"])
        results.append(merged)

    judged = [r for r in results if r["judge"] is not None]
    n = len(results)
    summary = {
        "gate_version": report["summary"]["gate_version"],
        "rubric_version": report["summary"]["rubric_version"],
        "count": n,
        "judged_count": len(judged),
        "deterministic_pass_rate": report["summary"]["deterministic_pass_rate"],
        "judge_category_pass_rate": round(sum(r["judge"]["category_pass"] for r in judged) / len(judged), 3) if judged else None,
        "judge_all_criteria_pass_rate": round(sum(r["judge"]["criteria_pass"] for r in judged) / len(judged), 3) if judged else None,
        "overall_pass_rate": round(sum(r["overall_pass"] for r in results) / n, 3) if n else None,
        "by_gate": report["summary"]["by_gate"],
        "by_category": {},
    }
    for r in results:
        cat = summary["by_category"].setdefault(
            r["task_category"], {"n": 0, "deterministic_pass": 0, "overall_pass": 0})
        cat["n"] += 1
        cat["deterministic_pass"] += r["deterministic_pass"]
        cat["overall_pass"] += r["overall_pass"]

    # Most-frequent judge criterion failures — the "what to fix next" list.
    criterion_fails: dict[str, int] = {}
    for r in judged:
        for cid, c in r["judge"]["criteria"].items():
            if not c["pass"]:
                criterion_fails[cid] = criterion_fails.get(cid, 0) + 1
    summary["judge_criterion_failures"] = dict(
        sorted(criterion_fails.items(), key=lambda kv: -kv[1]))

    out = Path(args.out)
    out.write_text(json.dumps({"summary": summary, "results": results}, indent=2,
                              ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"judged report -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
