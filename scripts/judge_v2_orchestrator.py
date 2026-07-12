#!/usr/bin/env python3
"""Build, qualify, validate, and trust-audit paired judge-protocol-v2 runs."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

try:
    import judge_protocol_v2 as protocol
except ModuleNotFoundError:
    from scripts import judge_protocol_v2 as protocol


SYSTEMS = ("ft_v2", "candidate")
SESSIONS = ("session-a", "session-b")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def opaque_id(run_id: str, session: str, shard: str, token: str) -> str:
    raw = f"{run_id}|{session}|{shard}|{token}".encode()
    return "blind-" + hashlib.sha256(raw).hexdigest()[:20]


def qualification_case_bundle(
    case: dict[str, Any], *, run_id: str, session: str, shard_id: str
) -> dict[str, Any]:
    example_id = opaque_id(run_id, session, shard_id, case["qualification_id"])
    pack_hash = protocol.qualification_pack_sha256()
    bundle = {
        "example_id": example_id,
        "suite_version": protocol.SUITE_VERSION,
        "gate_version": "sf-gates-10",
        "rubric_version": "rubric-v0.1",
        "judge_protocol_version": protocol.JUDGE_PROTOCOL_VERSION,
        "calibration_sha256": pack_hash,
        "qualification_pack_sha256": pack_hash,
        "run_id": run_id,
        "session_id": session,
        "shard_id": shard_id,
        "task_category": case["task_category"],
        "expected_criteria": case["expected_criteria"],
        "action_contract": case["action_contract"],
        "machine_facts": case["machine_facts"],
        "context": case["context"],
        "question": case["question"],
        "answer": case["answer"],
    }
    bundle["judge_prompt"] = judge_prompt(bundle)
    bundle["bundle_sha256"] = protocol.sha256_json(protocol.bundle_hash_payload(bundle))
    return bundle


def judge_prompt(bundle: dict[str, Any]) -> str:
    reason_codes = ", ".join(sorted(protocol.REASON_CODES))
    return (
        f"Judge this blinded answer under {protocol.JUDGE_PROTOCOL_VERSION}. The action contract "
        "and machine facts are authoritative. Score exactly expected_criteria. X1 is qualitative "
        "semantic grounding only; X6 is direct lead/no header-or-bullet spam only. category_pass "
        "is the AND of category criteria. A pass result is {\"pass\":true}. Every failure must "
        f"include pass=false, a permitted reason_code ({reason_codes}), an 8-60 word explanation, "
        "and 1-3 evidence "
        "anchors. An answer_quote must be an exact 3-40 word answer substring quoted verbatim in "
        "the explanation. A context_pointer must be RFC6901 under /context, echo observed_value "
        "exactly, and be named in the explanation. Output one object with example_id, all version "
        "and hash fields, run_id, session_id, shard_id, judge (a stable string; not judge_id), criteria, and "
        "category_pass. Echo all provenance fields.\n\n"
        + json.dumps(
            {key: value for key, value in bundle.items() if key != "judge_prompt"},
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def load_source_bundle(path: Path) -> dict[str, dict[str, Any]]:
    rows = read_jsonl(path)
    result: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows, 1):
        protocol.validate_bundle(row, f"{path}:{index}")
        if row["example_id"] in result:
            raise ValueError(f"duplicate source ID {row['example_id']}")
        result[row["example_id"]] = row
    return result


def build_run(args: argparse.Namespace) -> int:
    out = Path(args.out_dir)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing non-empty output directory: {out}")
    baseline = load_source_bundle(Path(args.baseline_bundle))
    candidate = load_source_bundle(Path(args.candidate_bundle))
    if set(baseline) != set(candidate) or len(baseline) != 200:
        raise SystemExit("paired source bundles must cover the same 200 example IDs")
    run_id = args.run_id
    rng = random.Random(args.seed)
    example_ids = sorted(baseline)
    rng.shuffle(example_ids)
    pairs_per_shard = args.pairs_per_shard
    shards = [example_ids[i:i + pairs_per_shard] for i in range(0, 200, pairs_per_shard)]
    if any(len(shard) != pairs_per_shard for shard in shards):
        raise SystemExit("pairs_per_shard must divide 200")

    cases = protocol.load_qualification_cases()
    gold = protocol.load_qualification_gold()
    if set(cases) != set(gold):
        raise SystemExit("qualification case/gold coverage mismatch")
    private_plans: dict[str, dict[str, Any]] = {}
    for shard_index, ids in enumerate(shards):
        shard_id = f"{shard_index:02d}"
        for session_index, session in enumerate(SESSIONS):
            items: list[dict[str, Any]] = []
            crosswalk: dict[str, dict[str, Any]] = {}
            for system, source in (("ft_v2", baseline), ("candidate", candidate)):
                for example_id in ids:
                    original = source[example_id]
                    blind_id = opaque_id(run_id, session, shard_id, f"{system}|{example_id}")
                    template = dict(original)
                    template["example_id"] = blind_id
                    template["run_id"] = run_id
                    template["session_id"] = session
                    template["shard_id"] = shard_id
                    template.pop("bundle_sha256", None)
                    template.pop("judge_prompt", None)
                    items.append(template)
                    crosswalk[blind_id] = {
                        "kind": "suite",
                        "system": system,
                        "original_example_id": example_id,
                        "original_bundle": original,
                    }
            sentinel_ids = sorted(cases)
            start = (shard_index * 2 + session_index) % len(sentinel_ids)
            chosen = [sentinel_ids[(start + offset) % len(sentinel_ids)] for offset in range(2)]
            for qualification_id in chosen:
                bundle = qualification_case_bundle(
                    cases[qualification_id], run_id=run_id, session=session, shard_id=shard_id
                )
                bundle.pop("bundle_sha256", None)
                bundle.pop("judge_prompt", None)
                items.append(bundle)
                crosswalk[bundle["example_id"]] = {
                    "kind": "sentinel",
                    "qualification_id": qualification_id,
                }
            base_items = list(items)
            for attempt in range(1000):
                items = list(base_items)
                random.Random(f"{args.seed}|{session}|{shard_id}|{attempt}").shuffle(items)
                positions = {item["example_id"]: i for i, item in enumerate(items)}
                if all(
                    abs(
                        positions[opaque_id(run_id, session, shard_id, f"ft_v2|{example_id}")]
                        - positions[opaque_id(run_id, session, shard_id, f"candidate|{example_id}")]
                    ) > 1
                    for example_id in ids
                ):
                    break
            else:
                raise SystemExit(f"could not produce nonadjacent pairing for {shard_id}/{session}")
            private_plans[f"{shard_id}/{session}"] = {
                "items": items,
                "crosswalk": crosswalk,
                "suite_example_ids": ids,
            }

    qualification_crosswalk: dict[str, dict[str, str]] = {}
    for session in SESSIONS:
        rows = [
            qualification_case_bundle(case, run_id=run_id, session=session, shard_id="qualification")
            for case in cases.values()
        ]
        random.Random(f"{args.seed}|{session}|qualification").shuffle(rows)
        write_jsonl(out / "qualification" / f"{session}.input.jsonl", rows)
        qualification_crosswalk[session] = {
            row["example_id"]: next(
                qid for qid, case in cases.items() if case["answer"] == row["answer"]
                and case["question"] == row["question"]
            )
            for row in rows
        }
    write_json(out / "private" / "qualification_crosswalk.json", qualification_crosswalk)
    write_json(out / "private" / "shard_plans.json", private_plans)
    manifest = {
        "run_id": run_id,
        "seed": args.seed,
        "pairs_per_shard": pairs_per_shard,
        "shard_count": len(shards),
        "sessions": list(SESSIONS),
        "systems": list(SYSTEMS),
        "qualification_pack_sha256": protocol.qualification_pack_sha256(),
        "source_bundle_sha256": {
            "ft_v2": file_sha(Path(args.baseline_bundle)),
            "candidate": file_sha(Path(args.candidate_bundle)),
        },
        "source_bundle_paths": {
            "ft_v2": args.baseline_bundle,
            "candidate": args.candidate_bundle,
        },
    }
    manifest["manifest_sha256"] = protocol.sha256_json(manifest)
    write_json(out / "run_manifest.json", manifest)
    print(f"built paired run {run_id}: {len(shards)} shards, 200 pairs, 2 sessions")
    return 0


def load_verdict_map(path: Path) -> dict[str, dict[str, Any]]:
    rows = read_jsonl(path)
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        example_id = row.get("example_id")
        if not isinstance(example_id, str) or example_id in result:
            raise ValueError(f"invalid/duplicate verdict ID in {path}")
        result[example_id] = row
    return result


def assert_active_run(out: Path) -> None:
    quarantine = out / "QUARANTINE.json"
    if quarantine.exists():
        reason = json.loads(quarantine.read_text()).get("failure", "unspecified failure")
        raise ValueError(f"paired run is quarantined: {reason}")


def validate_receipt_hash(receipt: dict[str, Any], location: str) -> None:
    recorded = receipt.get("receipt_sha256")
    payload = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    if not isinstance(recorded, str) or recorded != protocol.sha256_json(payload):
        raise ValueError(f"{location} receipt SHA-256 mismatch")


def validate_qualification_receipt(out: Path, session: str) -> dict[str, Any]:
    receipt = json.loads((out / "qualification" / f"{session}.receipt.json").read_text())
    validate_receipt_hash(receipt, f"qualification:{session}")
    input_path = out / "qualification" / f"{session}.input.jsonl"
    output_path = out / "qualification" / f"{session}.output.jsonl"
    if receipt.get("input_sha256") != file_sha(input_path):
        raise ValueError(f"qualification:{session} input changed after scoring")
    if receipt.get("output_sha256") != file_sha(output_path):
        raise ValueError(f"qualification:{session} output changed after scoring")
    if receipt.get("qualification_pack_sha256") != protocol.qualification_pack_sha256():
        raise ValueError(f"qualification:{session} pack hash mismatch")
    if (
        receipt.get("qualified") is not True
        or receipt.get("case_count") != 26
        or receipt.get("decision_correct") != 240
        or receipt.get("decision_total") != 240
        or receipt.get("gold_evidence_validated") is not True
    ):
        raise ValueError(f"qualification:{session} receipt does not prove hardened perfect scoring")
    return receipt


def validate_manifest(out: Path) -> dict[str, Any]:
    manifest = json.loads((out / "run_manifest.json").read_text())
    recorded = manifest.get("manifest_sha256")
    payload = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if recorded != protocol.sha256_json(payload):
        raise ValueError("run manifest SHA-256 mismatch")
    for system in SYSTEMS:
        source = Path(manifest["source_bundle_paths"][system])
        if manifest["source_bundle_sha256"].get(system) != file_sha(source):
            raise ValueError(f"{system} source bundle changed after run build")
    return manifest


def write_quarantine(args: argparse.Namespace, failure: Exception) -> None:
    out = Path(args.out_dir)
    target = out / "QUARANTINE.json"
    if target.exists() or args.command not in {"validate-shard", "audit-trust"}:
        return
    manifest_path = out / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    record = {
        "status": "quarantined",
        "run_id": manifest.get("run_id"),
        "failure": str(failure),
        "downstream_scoring_permitted": False,
        "selective_retry_permitted": False,
    }
    if args.command == "validate-shard":
        verdict_path = Path(args.verdicts)
        if not verdict_path.exists():
            return
        record.update({
            "failed_session": args.session,
            "failed_shard": f"{args.shard:02d}",
            "output_sha256": file_sha(verdict_path),
        })
    else:
        trust_report = out / "trust" / "system_trust.json"
        record.update({
            "failed_phase": "audit-trust",
            "trust_report_sha256": file_sha(trust_report) if trust_report.exists() else None,
        })
    write_json(target, record)


def score_exact_gold(
    verdicts: dict[str, dict[str, Any]], bundles: dict[str, dict[str, Any]],
    crosswalk: dict[str, str], location: str,
) -> dict[str, Any]:
    protocol.validate_batch(verdicts, bundles, location)
    gold = protocol.load_qualification_gold()
    if set(verdicts) != set(crosswalk):
        raise ValueError(f"{location} qualification coverage mismatch")
    decision_total = decision_correct = 0
    errors: list[str] = []
    for blind_id, verdict in verdicts.items():
        qualification_id = crosswalk[blind_id]
        expected = gold[qualification_id]
        for criterion_id, expected_pass in expected["criteria"].items():
            decision_total += 1
            actual = verdict["criteria"][criterion_id]
            decision_correct += actual["pass"] is expected_pass
            if actual["pass"] is not expected_pass:
                errors.append(
                    f"{qualification_id}:{criterion_id} decision {actual['pass']} != {expected_pass}"
                )
            if not expected_pass:
                failure = expected["failures"][criterion_id]
                if actual.get("reason_code") not in failure["allowed_reason_codes"]:
                    errors.append(f"{qualification_id}:{criterion_id} reason_code misses gold")
                anchors = actual.get("evidence", [])
                quotes = {anchor.get("quote") for anchor in anchors if anchor.get("kind") == "answer_quote"}
                pointers = {
                    anchor.get("pointer") for anchor in anchors if anchor.get("kind") == "context_pointer"
                }
                if len(quotes) < failure["minimum_quotes"]:
                    errors.append(f"{qualification_id}:{criterion_id} too few gold answer quotes")
                if len(pointers) < failure["minimum_pointers"]:
                    errors.append(f"{qualification_id}:{criterion_id} too few gold context pointers")
                if any(quote not in failure["allowed_answer_quotes"] for quote in quotes):
                    errors.append(f"{qualification_id}:{criterion_id} answer quote misses gold")
                if any(pointer not in failure["allowed_context_pointers"] for pointer in pointers):
                    errors.append(f"{qualification_id}:{criterion_id} context pointer misses gold")
        decision_total += 1
        decision_correct += verdict["category_pass"] is expected["category_pass"]
        if verdict["category_pass"] is not expected["category_pass"]:
            errors.append(
                f"{qualification_id}:category_pass {verdict['category_pass']} != {expected['category_pass']}"
            )
    if errors or decision_correct != decision_total:
        raise ValueError(
            f"{location} qualification score {decision_correct}/{decision_total}; perfect required; "
            + "; ".join(errors)
        )
    return {
        "case_count": len(verdicts),
        "decision_correct": decision_correct,
        "decision_total": decision_total,
        "gold_evidence_validated": True,
    }


def qualify(args: argparse.Namespace) -> int:
    out = Path(args.out_dir)
    assert_active_run(out)
    session = args.session
    receipt_target = out / "qualification" / f"{session}.receipt.json"
    if receipt_target.exists():
        raise ValueError("qualified session receipt already exists; refusing replacement")
    input_path = out / "qualification" / f"{session}.input.jsonl"
    bundles = {row["example_id"]: row for row in read_jsonl(input_path)}
    verdicts = load_verdict_map(Path(args.verdicts))
    crosswalk = json.loads((out / "private" / "qualification_crosswalk.json").read_text())[session]
    score = score_exact_gold(verdicts, bundles, crosswalk, f"qualification:{session}")
    judge_ids = {row.get("judge") for row in verdicts.values()}
    if len(judge_ids) != 1:
        raise SystemExit("qualification must use one stable judge identity")
    receipt = {
        "qualified": True,
        "run_id": json.loads((out / "run_manifest.json").read_text())["run_id"],
        "session_id": session,
        "judge": next(iter(judge_ids)),
        "qualification_pack_sha256": protocol.qualification_pack_sha256(),
        "input_sha256": file_sha(input_path),
        "output_sha256": file_sha(Path(args.verdicts)),
        **score,
    }
    receipt["receipt_sha256"] = protocol.sha256_json(receipt)
    write_json(out / "qualification" / f"{session}.receipt.json", receipt)
    print(json.dumps(receipt, indent=2))
    return 0


def unlock(args: argparse.Namespace) -> int:
    out = Path(args.out_dir)
    assert_active_run(out)
    validate_manifest(out)
    session, shard_id = args.session, f"{args.shard:02d}"
    receipt = validate_qualification_receipt(out, session)
    if not receipt.get("qualified") or receipt.get("session_id") != session:
        raise SystemExit("valid session qualification receipt required")
    previous_hash = None
    if args.shard:
        previous = out / "shards" / f"{args.shard-1:02d}" / f"{session}.receipt.json"
        previous_receipt = json.loads(previous.read_text())
        validate_receipt_hash(previous_receipt, f"shard:{args.shard-1:02d}:{session}")
        if not previous_receipt.get("valid"):
            raise SystemExit("previous shard receipt is not valid")
        agreement_path = out / "shards" / f"{args.shard-1:02d}" / "agreement.json"
        if not agreement_path.exists():
            raise ValueError("both sessions and prior-shard agreement statistics are required")
        previous_hash = previous_receipt["receipt_sha256"]
    plans = json.loads((out / "private" / "shard_plans.json").read_text())
    plan = plans[f"{shard_id}/{session}"]
    rows = []
    for template in plan["items"]:
        row = dict(template)
        row["qualification_attestation_sha256"] = receipt["receipt_sha256"]
        row["previous_shard_receipt_sha256"] = previous_hash
        row["judge_prompt"] = judge_prompt(row)
        row["bundle_sha256"] = protocol.sha256_json(protocol.bundle_hash_payload(row))
        rows.append(row)
    input_path = out / "shards" / shard_id / f"{session}.input.jsonl"
    if input_path.exists():
        raise SystemExit("shard input already unlocked; no retries in the same run")
    write_jsonl(input_path, rows)
    crosswalk = plan["crosswalk"]
    write_json(out / "private" / "shards" / shard_id / f"{session}.crosswalk.json", crosswalk)
    print(f"unlocked {session} shard {shard_id}: {len(rows)} blinded items")
    return 0


def validate_shard(args: argparse.Namespace) -> int:
    out = Path(args.out_dir)
    assert_active_run(out)
    validate_manifest(out)
    session, shard_id = args.session, f"{args.shard:02d}"
    receipt_target = out / "shards" / shard_id / f"{session}.receipt.json"
    if receipt_target.exists() or any(
        (out / "validated" / session / f"{shard_id}.{system}.jsonl").exists() for system in SYSTEMS
    ):
        raise ValueError("shard already has validated artifacts; selective revalidation is forbidden")
    input_path = out / "shards" / shard_id / f"{session}.input.jsonl"
    bundles = {row["example_id"]: row for row in read_jsonl(input_path)}
    verdict_path = Path(args.verdicts)
    verdicts = load_verdict_map(verdict_path)
    protocol.validate_batch(verdicts, bundles, f"shard:{shard_id}:{session}")
    crosswalk = json.loads(
        (out / "private" / "shards" / shard_id / f"{session}.crosswalk.json").read_text()
    )
    sentinel_map = {
        blind_id: item["qualification_id"]
        for blind_id, item in crosswalk.items() if item["kind"] == "sentinel"
    }
    if sentinel_map:
        score_exact_gold(
            {blind_id: verdicts[blind_id] for blind_id in sentinel_map},
            {blind_id: bundles[blind_id] for blind_id in sentinel_map},
            sentinel_map,
            f"sentinel:{shard_id}:{session}",
        )
    judge_ids = {row.get("judge") for row in verdicts.values()}
    qualification = validate_qualification_receipt(out, session)
    if judge_ids != {qualification["judge"]}:
        raise ValueError("shard judge identity differs from qualified session")
    by_system: dict[str, list[dict[str, Any]]] = {system: [] for system in SYSTEMS}
    for blind_id, mapping in crosswalk.items():
        if mapping["kind"] != "suite":
            continue
        original = mapping["original_bundle"]
        verdict = dict(verdicts[blind_id])
        verdict["example_id"] = mapping["original_example_id"]
        verdict["bundle_sha256"] = original["bundle_sha256"]
        verdict["shard_id"] = shard_id
        by_system[mapping["system"]].append(verdict)
    for system, rows in by_system.items():
        rows.sort(key=lambda row: row["example_id"])
        write_jsonl(out / "validated" / session / f"{shard_id}.{system}.jsonl", rows)
    validated_sha = {
        system: file_sha(out / "validated" / session / f"{shard_id}.{system}.jsonl")
        for system in SYSTEMS
    }
    receipt = {
        "valid": True,
        "run_id": qualification["run_id"],
        "session_id": session,
        "judge": qualification["judge"],
        "shard_id": shard_id,
        "input_sha256": file_sha(input_path),
        "output_sha256": file_sha(verdict_path),
        "qualification_receipt_sha256": qualification["receipt_sha256"],
        "previous_shard_receipt_sha256": bundles[next(iter(bundles))].get("previous_shard_receipt_sha256"),
        "sentinel_count": len(sentinel_map),
        "suite_count": sum(len(rows) for rows in by_system.values()),
        "validated_output_sha256": validated_sha,
    }
    receipt["receipt_sha256"] = protocol.sha256_json(receipt)
    write_json(receipt_target, receipt)
    write_shard_agreement_if_ready(out, shard_id)
    print(json.dumps(receipt, indent=2))
    return 0


def write_shard_agreement_if_ready(out: Path, shard_id: str) -> None:
    receipt_paths = [out / "shards" / shard_id / f"{session}.receipt.json" for session in SESSIONS]
    if not all(path.exists() for path in receipt_paths):
        return
    for session, path in zip(SESSIONS, receipt_paths):
        receipt = json.loads(path.read_text())
        validate_receipt_hash(receipt, f"shard:{shard_id}:{session}")
        if not receipt.get("valid"):
            raise ValueError(f"shard:{shard_id}:{session} is not valid")
        for system in SYSTEMS:
            validated = out / "validated" / session / f"{shard_id}.{system}.jsonl"
            if receipt.get("validated_output_sha256", {}).get(system) != file_sha(validated):
                raise ValueError(f"shard:{shard_id}:{session}:{system} validated output changed")
    report: dict[str, Any] = {"shard_id": shard_id, "systems": {}}
    manifest = validate_manifest(out)
    source_bundles = {
        system: load_source_bundle(Path(manifest["source_bundle_paths"][system])) for system in SYSTEMS
    }
    for system in SYSTEMS:
        session_rows = {
            session: {
                row["example_id"]: row
                for row in read_jsonl(out / "validated" / session / f"{shard_id}.{system}.jsonl")
            }
            for session in SESSIONS
        }
        for session in SESSIONS:
            subset = {
                example_id: source_bundles[system][example_id]
                for example_id in session_rows[session]
            }
            protocol.validate_batch(
                session_rows[session], subset, f"shard:{shard_id}:{system}:{session}"
            )
        report["systems"][system] = protocol.agreement_stats(
            session_rows["session-a"], session_rows["session-b"]
        )
        protocol.reject_asymmetric_constant_pass(
            session_rows["session-a"], session_rows["session-b"],
            f"shard:{shard_id}:{system}",
        )
    write_json(out / "shards" / shard_id / "agreement.json", report)


def audit_trust(args: argparse.Namespace) -> int:
    out = Path(args.out_dir)
    assert_active_run(out)
    manifest = validate_manifest(out)
    reports: dict[str, Any] = {}
    combined: dict[str, dict[str, dict[str, Any]]] = {}
    for session in SESSIONS:
        previous_hash = None
        qualification = validate_qualification_receipt(out, session)
        for shard in range(manifest["shard_count"]):
            receipt = json.loads((out / "shards" / f"{shard:02d}" / f"{session}.receipt.json").read_text())
            validate_receipt_hash(receipt, f"shard:{shard:02d}:{session}")
            if not receipt.get("valid") or receipt.get("session_id") != session:
                raise ValueError("invalid shard receipt")
            shard_dir = out / "shards" / f"{shard:02d}"
            if receipt.get("input_sha256") != file_sha(shard_dir / f"{session}.input.jsonl"):
                raise ValueError("shard input changed after validation")
            if receipt.get("output_sha256") != file_sha(shard_dir / f"{session}.output.jsonl"):
                raise ValueError("raw shard output changed after validation")
            for system in SYSTEMS:
                validated = out / "validated" / session / f"{shard:02d}.{system}.jsonl"
                if receipt.get("validated_output_sha256", {}).get(system) != file_sha(validated):
                    raise ValueError("normalized shard output changed after validation")
            if receipt.get("qualification_receipt_sha256") != qualification["receipt_sha256"]:
                raise ValueError("shard qualification receipt mismatch")
            if receipt.get("previous_shard_receipt_sha256") != previous_hash:
                raise ValueError("broken shard receipt chain")
            previous_hash = receipt["receipt_sha256"]

    for shard in range(manifest["shard_count"]):
        agreement_path = out / "shards" / f"{shard:02d}" / "agreement.json"
        if not agreement_path.exists():
            raise ValueError(f"missing per-shard agreement statistics for shard {shard:02d}")

    combined_rows: dict[str, dict[str, list[dict[str, Any]]]] = {
        system: {session: [] for session in SESSIONS} for system in SYSTEMS
    }
    for system in SYSTEMS:
        combined[system] = {}
        for session in SESSIONS:
            rows: list[dict[str, Any]] = []
            for shard in range(manifest["shard_count"]):
                rows.extend(read_jsonl(out / "validated" / session / f"{shard:02d}.{system}.jsonl"))
            by_id = {row["example_id"]: row for row in rows}
            if len(rows) != 200 or len(by_id) != 200:
                raise ValueError(f"{system}/{session} does not cover exactly 200 unique examples")
            combined[system][session] = by_id
            combined_rows[system][session] = sorted(rows, key=lambda row: row["example_id"])
        stats = protocol.agreement_stats(combined[system]["session-a"], combined[system]["session-b"])
        protocol.reject_asymmetric_constant_pass(
            combined[system]["session-a"], combined[system]["session-b"], f"combined:{system}"
        )
        reports[system] = {**stats, **protocol.trust_result(stats)}
    source_bundles = {
        system: load_source_bundle(Path(manifest["source_bundle_paths"][system])) for system in SYSTEMS
    }
    for system in SYSTEMS:
        for session in SESSIONS:
            protocol.validate_batch(
                combined[system][session], source_bundles[system], f"combined:{system}:{session}"
            )
    paired_session_batches: dict[str, dict[str, dict[str, Any]]] = {}
    for session in SESSIONS:
        all_verdicts: dict[str, dict[str, Any]] = {}
        all_bundles: dict[str, dict[str, Any]] = {}
        for system in SYSTEMS:
            for example_id, verdict in combined[system][session].items():
                key = f"{system}:{example_id}"
                all_verdicts[key] = verdict
                all_bundles[key] = source_bundles[system][example_id]
        protocol.validate_batch(all_verdicts, all_bundles, f"combined:{session}")
        paired_session_batches[session] = all_verdicts
    protocol.reject_asymmetric_constant_pass(
        paired_session_batches["session-a"], paired_session_batches["session-b"], "combined"
    )
    overall = all(report["trusted"] for report in reports.values())
    trust_report = {
        "run_id": manifest["run_id"],
        "judge_protocol_version": protocol.JUDGE_PROTOCOL_VERSION,
        "qualification_pack_sha256": protocol.qualification_pack_sha256(),
        "systems": reports,
        "overall_trusted": overall,
    }
    write_json(out / "trust" / "system_trust.json", trust_report)
    if not overall:
        write_quarantine(args, ValueError("one or more per-system trust gates failed"))
        print(json.dumps(trust_report, indent=2))
        return 1
    for system in SYSTEMS:
        for session in SESSIONS:
            write_jsonl(out / "systems" / system / f"{session}.jsonl", combined_rows[system][session])
    receipt = dict(trust_report)
    receipt["manifest_sha256"] = manifest["manifest_sha256"]
    receipt["source_bundle_sha256"] = manifest["source_bundle_sha256"]
    receipt["qualification_receipt_sha256"] = {
        session: json.loads((out / "qualification" / f"{session}.receipt.json").read_text())["receipt_sha256"]
        for session in SESSIONS
    }
    receipt["primary_output_sha256"] = {
        system: {
            session: file_sha(out / "systems" / system / f"{session}.jsonl")
            for session in SESSIONS
        }
        for system in SYSTEMS
    }
    receipt["trust_report_sha256"] = file_sha(out / "trust" / "system_trust.json")
    receipt["receipt_sha256"] = protocol.sha256_json(receipt)
    write_json(out / "trust" / "trusted_run_receipt.json", receipt)
    print(json.dumps(receipt, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--baseline-bundle", required=True)
    build.add_argument("--candidate-bundle", required=True)
    build.add_argument("--out-dir", required=True)
    build.add_argument("--run-id", required=True)
    build.add_argument("--seed", type=int, default=1402)
    build.add_argument("--pairs-per-shard", type=int, default=10)
    build.set_defaults(func=build_run)
    qualify_p = sub.add_parser("qualify")
    qualify_p.add_argument("--out-dir", required=True)
    qualify_p.add_argument("--session", choices=SESSIONS, required=True)
    qualify_p.add_argument("--verdicts", required=True)
    qualify_p.set_defaults(func=qualify)
    unlock_p = sub.add_parser("unlock")
    unlock_p.add_argument("--out-dir", required=True)
    unlock_p.add_argument("--session", choices=SESSIONS, required=True)
    unlock_p.add_argument("--shard", type=int, required=True)
    unlock_p.set_defaults(func=unlock)
    validate_p = sub.add_parser("validate-shard")
    validate_p.add_argument("--out-dir", required=True)
    validate_p.add_argument("--session", choices=SESSIONS, required=True)
    validate_p.add_argument("--shard", type=int, required=True)
    validate_p.add_argument("--verdicts", required=True)
    validate_p.set_defaults(func=validate_shard)
    audit = sub.add_parser("audit-trust")
    audit.add_argument("--out-dir", required=True)
    audit.set_defaults(func=audit_trust)
    return ap


def main() -> int:
    args = parser().parse_args()
    try:
        return args.func(args)
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        write_quarantine(args, exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
