#!/usr/bin/env python3
"""Merge two independent judge passes; surface disagreements for adjudication.

Usage:
    .venv/bin/python scripts/merge_judgments.py \
        --pass-a <verdicts_a.jsonl ...> --pass-b <verdicts_b.jsonl ...> \
        --out judge_verdicts.jsonl --disagreements disagreements.jsonl

Implements the eval-plan judging protocol: every answer judged twice;
category_pass agreement -> final verdict (per-criterion: strict AND of both
judges, so a criterion either judge failed stays failed); category_pass
disagreement -> NOT emitted, written to the disagreements file for a human
(or a third adjudicator) to resolve. Adjudicated verdicts are appended to the
output by hand, with "judge": "adjudicated:<who>".
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(paths: list[str]) -> dict[str, dict]:
    verdicts: dict[str, dict] = {}
    for p in paths:
        for line in Path(p).read_text().splitlines():
            if line.strip():
                v = json.loads(line)
                verdicts[v["example_id"]] = v
    return verdicts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass-a", nargs="+", required=True)
    ap.add_argument("--pass-b", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--disagreements", required=True)
    args = ap.parse_args()

    a, b = load(args.pass_a), load(args.pass_b)
    if set(a) != set(b):
        raise SystemExit(f"pass coverage differs: only-a={sorted(set(a)-set(b))} only-b={sorted(set(b)-set(a))}")

    merged, disputes = [], []
    for example_id in sorted(a):
        va, vb = a[example_id], b[example_id]
        if va["category_pass"] == vb["category_pass"]:
            criteria = {}
            for cid in sorted(set(va["criteria"]) | set(vb["criteria"])):
                ca = va["criteria"].get(cid, {"pass": True, "reason": "not scored"})
                cb = vb["criteria"].get(cid, {"pass": True, "reason": "not scored"})
                criteria[cid] = {
                    "pass": ca["pass"] and cb["pass"],
                    "reason": ca["reason"] if not ca["pass"] or cb["pass"] else cb["reason"],
                }
            merged.append({"example_id": example_id, "criteria": criteria,
                           "category_pass": va["category_pass"],
                           "judge": f"{va.get('judge','a')}+{vb.get('judge','b')}"})
        else:
            disputes.append({"example_id": example_id, "pass_a": va, "pass_b": vb})

    Path(args.out).write_text(
        "".join(json.dumps(m, ensure_ascii=False) + "\n" for m in merged))
    Path(args.disagreements).write_text(
        "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in disputes))
    print(f"agreed: {len(merged)} -> {args.out}\n"
          f"disagreements: {len(disputes)} -> {args.disagreements}"
          + ("" if not disputes else "  (adjudicate, then append to the verdicts file)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
