#!/usr/bin/env python3
"""Validate and freeze the non-suite judge-protocol-v2 qualification pack."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    import judge_protocol_v2 as protocol
except ModuleNotFoundError:
    from scripts import judge_protocol_v2 as protocol


ROOT = Path(__file__).resolve().parents[1]


def pointer_get(document, pointer: str):
    value = document
    for raw in pointer.split("/")[1:]:
        token = raw.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def spans(text: str, size: int = 16) -> set[str]:
    tokens = " ".join(text.casefold().split()).split()
    return {" ".join(tokens[i:i + size]) for i in range(max(0, len(tokens) - size + 1))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-manifest", action="store_true")
    args = ap.parse_args()
    cases = protocol.load_qualification_cases()
    gold = protocol.load_qualification_gold()
    if len(cases) != 26 or set(cases) != set(gold):
        raise SystemExit("qualification pack must contain 26 matching unique cases/gold rows")
    decision_coverage: dict[str, set[bool]] = {}
    for qualification_id, case in cases.items():
        expected = list(protocol.expected_criteria(case["task_category"]))
        if case["expected_criteria"] != expected:
            raise SystemExit(f"{qualification_id}: expected criteria mismatch")
        answer_key = gold[qualification_id]
        if set(answer_key["criteria"]) != set(expected):
            raise SystemExit(f"{qualification_id}: gold criteria mismatch")
        category_ids = protocol.CATEGORY_CRITERIA[case["task_category"]]
        category_pass = all(answer_key["criteria"][cid] for cid in category_ids)
        if answer_key["category_pass"] is not category_pass:
            raise SystemExit(f"{qualification_id}: category roll-up mismatch")
        false_ids = {cid for cid, passed in answer_key["criteria"].items() if not passed}
        if set(answer_key["failures"]) != false_ids:
            raise SystemExit(f"{qualification_id}: failure key mismatch")
        for criterion_id, passed in answer_key["criteria"].items():
            decision_coverage.setdefault(criterion_id, set()).add(passed)
        for criterion_id, failure in answer_key["failures"].items():
            for quote in failure["allowed_answer_quotes"]:
                if quote not in case["answer"]:
                    raise SystemExit(f"{qualification_id}/{criterion_id}: non-exact answer quote")
            for pointer in failure["allowed_context_pointers"]:
                pointer_get({"context": case["context"]}, pointer)
    missing_sides = {cid: sorted(values) for cid, values in decision_coverage.items() if values != {False, True}}
    if len(decision_coverage) != 37 or missing_sides:
        raise SystemExit(f"criterion pass/fail coverage incomplete: {missing_sides}")

    eval_ids: set[str] = set()
    eval_spans: set[str] = set()
    for path in (ROOT / "eval" / "v1" / "cases").rglob("*.json"):
        row = json.loads(path.read_text())
        eval_ids.add(row["example_id"])
        eval_spans |= spans(row["context"]["request"]["user_question"])
        eval_spans |= spans(row["target_response"]["text"])
    for generation_path in (
        ROOT / "data/checks/iteration13-judge-protocol/ft_v2/suite_generations.jsonl",
        ROOT / "data/checks/iteration13-judge-protocol/ft_v7-micro-wrapper-v4/suite_generations.jsonl",
    ):
        for row in map(json.loads, generation_path.read_text().splitlines()):
            eval_spans |= spans(row["answer"])
    qualification_spans: set[str] = set()
    for qualification_id, case in cases.items():
        if qualification_id in eval_ids:
            raise SystemExit(f"qualification ID collides with eval: {qualification_id}")
        qualification_spans |= spans(case["question"])
        qualification_spans |= spans(case["answer"])
    overlap = qualification_spans & eval_spans
    if overlap:
        raise SystemExit(f"qualification pack shares a 16-token span with suite/system evidence: {sorted(overlap)[:1]}")

    manifest = {
        "judge_protocol_version": protocol.JUDGE_PROTOCOL_VERSION,
        "qualification_pack_version": "judge-qualification-v2",
        "case_count": len(cases),
        "criterion_count": len(decision_coverage),
        "all_criteria_have_pass_and_fail": True,
        "suite_id_overlap": 0,
        "suite_16_token_span_overlap": 0,
        "files": {},
    }
    for path in (protocol.PROTOCOL_PATH, protocol.QUALIFICATION_CASES_PATH, protocol.QUALIFICATION_GOLD_PATH):
        manifest["files"][path.name] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }
    manifest["qualification_pack_sha256"] = protocol.qualification_pack_sha256()
    if args.write_manifest:
        target = protocol.PROTOCOL_DIR / "manifest.json"
        target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        print(f"wrote {target}")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
