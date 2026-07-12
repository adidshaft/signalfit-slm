#!/usr/bin/env python3
"""Merge two independent judge passes; surface disagreements for adjudication.

Usage:
    .venv/bin/python scripts/merge_judgments.py \
        --pass-a <verdicts_a.jsonl ...> --pass-b <verdicts_b.jsonl ...> \
        --out judge_verdicts.jsonl --disagreements disagreements.jsonl

Implements judge-protocol-v1: every answer is judged twice with exact bundle
provenance. Fully identical pass/fail decisions are emitted; any category or
qualitative-criterion disagreement is written with both reasons and the
original bundle for independent adjudication. Adjudicated verdicts are
appended to the output with "judge": "adjudicated:<who>".
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

try:
    import judge_protocol as protocol_v1
    import judge_protocol_v2 as protocol_v2
except ModuleNotFoundError:  # imported as scripts.merge_judgments in tests
    from scripts import judge_protocol as protocol_v1
    from scripts import judge_protocol_v2 as protocol_v2

VERSION_KEYS = protocol_v1.VERSION_KEYS
stamp_from = protocol_v1.stamp_from


def protocol_for_bundle(bundle: dict):
    version = bundle.get("judge_protocol_version")
    if version == protocol_v1.JUDGE_PROTOCOL_VERSION:
        return protocol_v1
    if version == protocol_v2.JUDGE_PROTOCOL_VERSION:
        return protocol_v2
    raise ValueError(f"unsupported judge protocol {version!r}")


_CROSS_CUTTING_ID = re.compile(r"^(X[1-7])(?:\b|$)", re.IGNORECASE)


def canonical_criterion_id(raw: str) -> str:
    """Map judge label variants such as 'X1 grounding' to rubric id 'X1'."""
    match = _CROSS_CUTTING_ID.match(raw.strip())
    return match.group(1).upper() if match else raw.strip()


def canonicalize_criteria(criteria: dict[str, dict]) -> dict[str, dict]:
    """Canonicalize aliases while preserving strict-AND failure semantics."""
    normalized: dict[str, dict] = {}
    for raw_id, criterion in criteria.items():
        cid = canonical_criterion_id(raw_id)
        current = {"pass": bool(criterion["pass"]), "reason": criterion["reason"]}
        if cid not in normalized:
            normalized[cid] = current
            continue
        previous = normalized[cid]
        normalized[cid] = {
            "pass": previous["pass"] and current["pass"],
            "reason": (
                previous["reason"] if not previous["pass"]
                else current["reason"] if not current["pass"]
                else previous["reason"]
            ),
        }
    return normalized


def load(paths: list[str], bundles: dict[str, dict] | None = None, pass_name: str = "pass") -> dict[str, dict]:
    verdicts: dict[str, dict] = {}
    for p in paths:
        for line_number, line in enumerate(Path(p).read_text().splitlines(), 1):
            if line.strip():
                v = json.loads(line)
                example_id = v.get("example_id")
                if not isinstance(example_id, str) or not example_id:
                    raise SystemExit(f"{p}:{line_number}: missing example_id")
                if example_id in verdicts:
                    raise SystemExit(f"duplicate verdict for {example_id} in {pass_name}")
                if bundles is None:
                    v["criteria"] = canonicalize_criteria(v["criteria"])
                else:
                    bundle = bundles.get(example_id)
                    if bundle is None:
                        raise SystemExit(f"{pass_name} verdict {example_id} has no bundle row")
                    try:
                        protocol_for_bundle(bundle).validate_verdict(v, bundle, f"{p}:{line_number}")
                    except ValueError as exc:
                        raise SystemExit(str(exc)) from exc
                verdicts[v["example_id"]] = v
    return verdicts


def load_bundles(path: str) -> dict[str, dict]:
    bundles: dict[str, dict] = {}
    for line_number, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        example_id = row.get("example_id")
        if not isinstance(example_id, str) or not example_id:
            raise SystemExit(f"{path}:{line_number}: missing bundle example_id")
        if example_id in bundles:
            raise SystemExit(f"duplicate bundle row for {example_id}")
        try:
            protocol_for_bundle(row).validate_bundle(row, f"{path}:{line_number}")
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        bundles[example_id] = row
    stamps = {
        tuple(row.get(key) for key in VERSION_KEYS) + (row.get("calibration_sha256"),)
        for row in bundles.values()
    }
    if len(stamps) != 1:
        raise SystemExit(f"bundle contains mixed protocol provenance: {sorted(stamps)}")
    return bundles


def agreement_stats(a: dict[str, dict], b: dict[str, dict]) -> dict:
    n = len(a)
    both_pass = both_fail = a_pass_b_fail = a_fail_b_pass = 0
    criterion_same = criterion_total = 0
    for example_id in a:
        av = bool(a[example_id]["category_pass"])
        bv = bool(b[example_id]["category_pass"])
        if av and bv:
            both_pass += 1
        elif not av and not bv:
            both_fail += 1
        elif av:
            a_pass_b_fail += 1
        else:
            a_fail_b_pass += 1
        for criterion_id in a[example_id]["criteria"]:
            criterion_total += 1
            criterion_same += (
                a[example_id]["criteria"][criterion_id]["pass"]
                == b[example_id]["criteria"][criterion_id]["pass"]
            )
    agreement = (both_pass + both_fail) / n if n else 0.0
    a_rate = (both_pass + a_pass_b_fail) / n if n else 0.0
    b_rate = (both_pass + a_fail_b_pass) / n if n else 0.0
    expected = a_rate * b_rate + (1 - a_rate) * (1 - b_rate)
    kappa = (agreement - expected) / (1 - expected) if expected < 1 else None
    return {
        "count": n,
        "category_agreement_count": both_pass + both_fail,
        "category_agreement_rate": round(agreement, 4),
        "category_confusion": {
            "both_pass": both_pass,
            "both_fail": both_fail,
            "a_pass_b_fail": a_pass_b_fail,
            "a_fail_b_pass": a_fail_b_pass,
        },
        "pass_a_rate": round(a_rate, 4),
        "pass_b_rate": round(b_rate, 4),
        "pass_rate_gap": round(abs(a_rate - b_rate), 4),
        "cohen_kappa": None if kappa is None else round(kappa, 4),
        "criterion_agreement_count": criterion_same,
        "criterion_count": criterion_total,
        "criterion_agreement_rate": round(criterion_same / criterion_total, 4) if criterion_total else 0.0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass-a", nargs="+", required=True)
    ap.add_argument("--pass-b", nargs="+", required=True)
    ap.add_argument("--bundle", required=True,
                    help="judge_bundle.jsonl that binds verdicts to exact answers")
    ap.add_argument("--out", required=True)
    ap.add_argument("--disagreements", required=True)
    ap.add_argument("--agreement-report")
    ap.add_argument("--trust-receipt")
    ap.add_argument("--system", choices=("ft_v2", "candidate"))
    args = ap.parse_args()

    bundles = load_bundles(args.bundle)
    protocol = protocol_for_bundle(next(iter(bundles.values())))
    if protocol is protocol_v2:
        if not args.trust_receipt or not args.system:
            raise SystemExit("judge-protocol-v2 merge requires --trust-receipt and --system")
        trust = json.loads(Path(args.trust_receipt).read_text())
        try:
            protocol_v2.validate_trust_receipt(trust, args.system)
        except ValueError as exc:
            raise SystemExit(f"judge-protocol-v2 merge blocked: {exc}") from exc
        expected_bundle_hash = trust.get("source_bundle_sha256", {}).get(args.system)
        actual_bundle_hash = hashlib.sha256(Path(args.bundle).read_bytes()).hexdigest()
        if expected_bundle_hash != actual_bundle_hash:
            raise SystemExit("bundle does not match trusted run receipt")
        expected_hashes = trust.get("primary_output_sha256", {}).get(args.system, {})
        for label, paths in (("session-a", args.pass_a), ("session-b", args.pass_b)):
            if len(paths) != 1 or expected_hashes.get(label) != hashlib.sha256(Path(paths[0]).read_bytes()).hexdigest():
                raise SystemExit(f"{label} output does not match trusted run receipt")
    a = load(args.pass_a, bundles, "pass-a")
    b = load(args.pass_b, bundles, "pass-b")
    if set(a) != set(b):
        raise SystemExit(f"pass coverage differs: only-a={sorted(set(a)-set(b))} only-b={sorted(set(b)-set(a))}")
    if set(a) != set(bundles):
        raise SystemExit(
            f"verdict coverage differs from bundle: missing={sorted(set(bundles)-set(a))[:5]} "
            f"extra={sorted(set(a)-set(bundles))[:5]}"
        )
    if protocol is protocol_v2:
        actual_stats = protocol_v2.agreement_stats(a, b)
        receipt_stats = trust["systems"][args.system]
        for key in (
            "count", "category_confusion", "raw_category_agreement_rate",
            "raw_cohen_kappa", "raw_pass_rate_gap",
        ):
            if actual_stats.get(key) != receipt_stats.get(key):
                raise SystemExit(f"trusted receipt {key} does not match supplied session outputs")
    judges_a = {v["judge"] for v in a.values()}
    judges_b = {v["judge"] for v in b.values()}
    if len(judges_a) != 1 or len(judges_b) != 1:
        raise SystemExit(f"each pass needs one stable judge identity: a={sorted(judges_a)} b={sorted(judges_b)}")
    if judges_a == judges_b:
        raise SystemExit("independent passes must use distinct judge identities")

    merged, disputes = [], []
    for example_id in sorted(a):
        va, vb = a[example_id], b[example_id]
        criterion_disagreements = sorted(
            criterion_id for criterion_id in va["criteria"]
            if va["criteria"][criterion_id]["pass"] != vb["criteria"][criterion_id]["pass"]
        )
        if va["category_pass"] == vb["category_pass"] and not criterion_disagreements:
            criteria = {}
            for cid in sorted(va["criteria"]):
                ca = va["criteria"][cid]
                cb = vb["criteria"][cid]
                if protocol is protocol_v2:
                    criteria[cid] = ca
                else:
                    criteria[cid] = {
                        "pass": ca["pass"] and cb["pass"],
                        "reason": ca["reason"] if not ca["pass"] or cb["pass"] else cb["reason"],
                    }
            bundle = bundles[example_id]
            merged.append({
                "example_id": example_id,
                **stamp_from(bundle),
                "calibration_sha256": bundle["calibration_sha256"],
                **(
                    {"qualification_pack_sha256": bundle["qualification_pack_sha256"]}
                    if protocol is protocol_v2 else {}
                ),
                "bundle_sha256": bundle["bundle_sha256"],
                "criteria": criteria,
                "category_pass": va["category_pass"],
                "judge": f"{va['judge']}+{vb['judge']}",
            })
        else:
            disputes.append({
                "example_id": example_id,
                **stamp_from(bundles[example_id]),
                "category_disagreement": va["category_pass"] != vb["category_pass"],
                "criterion_disagreements": criterion_disagreements,
                "bundle": bundles[example_id],
                "pass_a": va,
                "pass_b": vb,
            })

    Path(args.out).write_text(
        "".join(json.dumps(m, ensure_ascii=False) + "\n" for m in merged))
    Path(args.disagreements).write_text(
        "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in disputes))
    stats = agreement_stats(a, b)
    stats.update({
        **stamp_from(next(iter(bundles.values()))),
        "judge_a": next(iter(judges_a)),
        "judge_b": next(iter(judges_b)),
        "fully_agreed_count": len(merged),
        "adjudication_count": len(disputes),
    })
    agreement_path = Path(args.agreement_report) if args.agreement_report else Path(args.out).with_name("agreement_report.json")
    agreement_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n")
    kappa_text = "undefined" if stats["cohen_kappa"] is None else f"{stats['cohen_kappa']:.3f}"
    print(f"category agreement: {stats['category_agreement_count']}/{stats['count']} "
          f"({stats['category_agreement_rate']:.1%}); kappa={kappa_text}; "
          f"pass-rate gap={stats['pass_rate_gap']:.1%}\n"
          f"fully agreed: {len(merged)} -> {args.out}\n"
          f"adjudication required: {len(disputes)} -> {args.disagreements}\n"
          f"agreement report: {agreement_path}"
          + ("" if not disputes else "  (adjudicate, then append to the verdicts file)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
