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

An example's overall_pass = deterministic_pass AND category_pass AND every
cross-cutting criterion. The judged report keeps the full score quadruple;
verdict and exact-answer bundle provenance must match before scoring.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    from judge_protocol import VERSION_KEYS
    from merge_judgments import load_bundles, protocol_for_bundle
except ModuleNotFoundError:  # imported as scripts.apply_judge in tests
    from scripts.judge_protocol import VERSION_KEYS
    from scripts.merge_judgments import load_bundles, protocol_for_bundle


def synthesize_criteria(verdict_criteria: dict, facts: dict) -> dict:
    """Combine qualitative judge work with authoritative mechanical subchecks."""
    final_criteria = dict(verdict_criteria)
    qualitative_x1 = final_criteria["X1"]
    x1_reason = qualitative_x1.get("reason") or qualitative_x1.get("explanation") or "qualitative pass"
    numeric_x1 = facts["numeric_grounding"]
    final_criteria["X1"] = {
        "pass": bool(qualitative_x1["pass"] and numeric_x1["pass"]),
        "reason": (
            f"machine numeric_grounding={numeric_x1['pass']}; "
            f"qualitative: {x1_reason}"
        ),
    }
    final_criteria["X4"] = {
        "pass": bool(facts["followup_budget"]["pass"]),
        "reason": f"machine question_count={facts['followup_budget']['questions']}",
    }
    final_criteria["X5"] = {
        "pass": bool(facts["brand_check"]["pass"]),
        "reason": f"machine brand_matches={facts['brand_check']['found']}",
    }
    qualitative_x6 = final_criteria["X6"]
    x6_reason = qualitative_x6.get("reason") or qualitative_x6.get("explanation") or "qualitative pass"
    length_x6 = facts["rubric_word_range"]
    final_criteria["X6"] = {
        "pass": bool(qualitative_x6["pass"] and length_x6["pass"]),
        "reason": (
            f"machine word_range={length_x6['word_count']} in {length_x6['bounds']} "
            f"=> {length_x6['pass']}; qualitative: {x6_reason}"
        ),
    }
    return final_criteria


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--bundle", required=True,
                    help="judge bundle used to bind verdicts to exact answers")
    ap.add_argument("--out", required=True)
    ap.add_argument("--allow-missing", action="store_true",
                    help="tolerate examples without a verdict (default: error)")
    ap.add_argument("--trust-receipt")
    ap.add_argument("--system", choices=("ft_v2", "candidate"))
    args = ap.parse_args()

    report = json.loads(Path(args.report).read_text())
    bundles = load_bundles(args.bundle)
    protocol = protocol_for_bundle(next(iter(bundles.values())))
    trust = None
    if protocol.JUDGE_PROTOCOL_VERSION == "judge-protocol-v2":
        if args.allow_missing:
            sys.exit("judge-protocol-v2 forbids --allow-missing")
        if not args.trust_receipt or not args.system:
            sys.exit("judge-protocol-v2 apply requires --trust-receipt and --system")
        trust = json.loads(Path(args.trust_receipt).read_text())
        try:
            protocol.validate_trust_receipt(trust, args.system)
        except ValueError as exc:
            sys.exit(f"judge-protocol-v2 apply blocked: {exc}")
        expected_bundle_hash = trust.get("source_bundle_sha256", {}).get(args.system)
        actual_bundle_hash = hashlib.sha256(Path(args.bundle).read_bytes()).hexdigest()
        if expected_bundle_hash != actual_bundle_hash:
            sys.exit("bundle does not match trusted run receipt")
    try:
        protocol.validate_stamp(report["summary"], next(iter(bundles.values())), "report.summary")
    except (ValueError, StopIteration) as exc:
        sys.exit(str(exc))
    if report["summary"].get("calibration_sha256") != next(iter(bundles.values())).get("calibration_sha256"):
        sys.exit("report.summary calibration_sha256 mismatch")
    verdicts: dict[str, dict] = {}
    for line_number, line in enumerate(Path(args.verdicts).read_text().splitlines(), 1):
        if not line.strip():
            continue
        v = json.loads(line)
        if v["example_id"] in verdicts:
            sys.exit(f"duplicate verdict for {v['example_id']}")
        bundle = bundles.get(v["example_id"])
        if bundle is None:
            sys.exit(f"verdict for {v['example_id']} has no bundle row")
        try:
            protocol.validate_verdict(v, bundle, f"{args.verdicts}:{line_number}")
        except ValueError as exc:
            sys.exit(str(exc))
        verdicts[v["example_id"]] = v

    known = {r["example_id"] for r in report["results"]}
    unknown = set(verdicts) - known
    if unknown:
        sys.exit(f"verdicts for examples not in report: {sorted(unknown)}")
    missing = known - set(verdicts)
    if missing and not args.allow_missing:
        sys.exit(f"{len(missing)} examples lack a verdict (use --allow-missing to score anyway): "
                 f"{sorted(missing)[:5]}{'...' if len(missing) > 5 else ''}")
    if set(bundles) != known:
        sys.exit(
            f"bundle/report coverage mismatch: bundle-only={sorted(set(bundles)-known)[:5]} "
            f"report-only={sorted(known-set(bundles))[:5]}"
        )
    if protocol.JUDGE_PROTOCOL_VERSION == "judge-protocol-v2":
        try:
            protocol.validate_batch(verdicts, bundles, "apply")
        except ValueError as exc:
            sys.exit(str(exc))

    results = []
    for r in report["results"]:
        v = verdicts.get(r["example_id"])
        merged = dict(r)
        final_criteria = None
        if v is not None:
            facts = bundles[r["example_id"]]["machine_facts"]
            final_criteria = synthesize_criteria(v["criteria"], facts)
        # criteria_pass is the strict bar (rubric roll-up: cross_cutting AND
        # category): an answer with a judge-confirmed false qualitative claim
        # (X1) fails overall even when its category criteria all pass.
        merged["judge"] = None if v is None else {
            "judge": v.get("judge"),
            "category_pass": v["category_pass"],
            "criteria_pass": all(c["pass"] for c in final_criteria.values()),
            "criteria": final_criteria,
            "bundle_sha256": v["bundle_sha256"],
        }
        merged["overall_pass"] = bool(
            r["deterministic_pass"] and v and v["category_pass"]
            and merged["judge"]["criteria_pass"])
        results.append(merged)

    judged = [r for r in results if r["judge"] is not None]
    n = len(results)
    summary = {
        **{key: report["summary"][key] for key in VERSION_KEYS},
        "calibration_sha256": report["summary"]["calibration_sha256"],
        **(
            {
                "qualification_pack_sha256": report["summary"]["qualification_pack_sha256"],
                "paired_run_id": trust["run_id"],
                "trust_receipt_sha256": hashlib.sha256(Path(args.trust_receipt).read_bytes()).hexdigest(),
                "judged_system": args.system,
            }
            if trust is not None else {}
        ),
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
