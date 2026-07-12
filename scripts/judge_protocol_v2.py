#!/usr/bin/env python3
"""Competence, evidence, and trust rules for judge-protocol-v2."""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    from judge_protocol import (
        CATEGORY_CRITERIA,
        QUALITATIVE_CROSS_CUTTING,
        RUBRIC_LENGTH_BOUNDS,
        SUITE_VERSION,
        VERSION_KEYS,
        action_contract,
        canonical_json,
        expected_criteria,
        machine_facts,
        rubric_length_fact,
        sha256_json,
        stamp_from,
    )
except ModuleNotFoundError:
    from scripts.judge_protocol import (
        CATEGORY_CRITERIA,
        QUALITATIVE_CROSS_CUTTING,
        RUBRIC_LENGTH_BOUNDS,
        SUITE_VERSION,
        VERSION_KEYS,
        action_contract,
        canonical_json,
        expected_criteria,
        machine_facts,
        rubric_length_fact,
        sha256_json,
        stamp_from,
    )


REPO = Path(__file__).resolve().parent.parent
JUDGE_PROTOCOL_VERSION = "judge-protocol-v2"
PROTOCOL_DIR = REPO / "eval" / "judge_protocol_v2"
PROTOCOL_PATH = PROTOCOL_DIR / "protocol.json"
QUALIFICATION_CASES_PATH = PROTOCOL_DIR / "qualification_cases.jsonl"
QUALIFICATION_GOLD_PATH = PROTOCOL_DIR / "qualification_gold.jsonl"
REASON_CODES = {
    "contradicted",
    "unsupported",
    "omitted_required",
    "included_forbidden",
    "wrong_route",
    "wrong_count",
    "wrong_specificity",
    "wrong_care_level",
    "causal_overclaim",
    "unhedged_estimate",
    "population_personal_conflation",
    "indirect_or_spam",
}
TRUST_THRESHOLDS = {
    "category_agreement_rate": 0.80,
    "cohen_kappa": 0.60,
    "pass_rate_gap": 0.10,
}
GENERIC_EXPLANATIONS = {
    "unsupported",
    "conflicts with context",
    "conflicts with facts",
    "criterion not met",
    "not enough evidence",
    "does not satisfy",
    "fails the criterion",
}


def _bytes_hash(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def qualification_pack_sha256() -> str:
    return _bytes_hash([PROTOCOL_PATH, QUALIFICATION_CASES_PATH, QUALIFICATION_GOLD_PATH])


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_qualification_cases() -> dict[str, dict[str, Any]]:
    rows = load_jsonl(QUALIFICATION_CASES_PATH)
    return {row["qualification_id"]: row for row in rows}


def load_qualification_gold() -> dict[str, dict[str, Any]]:
    rows = load_jsonl(QUALIFICATION_GOLD_PATH)
    return {row["qualification_id"]: row for row in rows}


def bundle_hash_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "bundle_sha256"}


def validate_stamp(value: dict[str, Any], expected: dict[str, Any], location: str) -> None:
    for key in VERSION_KEYS:
        if value.get(key) != expected.get(key):
            raise ValueError(
                f"{location} {key} mismatch: {value.get(key)!r} != {expected.get(key)!r}"
            )


def validate_bundle(bundle: dict[str, Any], location: str) -> None:
    if bundle.get("suite_version") != SUITE_VERSION:
        raise ValueError(f"{location} suite_version mismatch")
    if bundle.get("judge_protocol_version") != JUDGE_PROTOCOL_VERSION:
        raise ValueError(f"{location} judge_protocol_version mismatch")
    pack_hash = qualification_pack_sha256()
    if bundle.get("qualification_pack_sha256") != pack_hash:
        raise ValueError(f"{location} qualification_pack_sha256 mismatch")
    if bundle.get("calibration_sha256") != pack_hash:
        raise ValueError(f"{location} calibration_sha256 mismatch")
    if bundle.get("bundle_sha256") != sha256_json(bundle_hash_payload(bundle)):
        raise ValueError(f"{location} bundle_sha256 does not match payload")
    if bundle.get("expected_criteria") != list(expected_criteria(bundle.get("task_category"))):
        raise ValueError(f"{location} expected_criteria mismatch")


def _pointer_get(document: Any, pointer: str) -> Any:
    if not isinstance(pointer, str) or not pointer.startswith("/context/"):
        raise ValueError("context pointer must identify a field below /context/")
    value = document
    for raw in pointer.split("/")[1:]:
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            try:
                value = value[int(token)]
            except (ValueError, IndexError) as exc:
                raise ValueError(f"unresolvable list pointer {pointer!r}") from exc
        elif isinstance(value, dict) and token in value:
            value = value[token]
        else:
            raise ValueError(f"unresolvable context pointer {pointer!r}")
    return value


def _normalize_explanation(explanation: str, evidence: list[dict[str, Any]]) -> str:
    normalized = explanation.casefold()
    for anchor in evidence:
        value = anchor.get("quote") or anchor.get("pointer") or ""
        if value:
            normalized = normalized.replace(str(value).casefold(), "<evidence>")
    normalized = re.sub(r"[^a-z0-9<>]+", " ", normalized)
    normalized = re.sub(r"(?:<evidence>\s*)+", "<evidence> ", normalized)
    return " ".join(normalized.split())


def validate_failure_result(
    result: dict[str, Any], bundle: dict[str, Any], location: str
) -> tuple[str, tuple[str, ...]]:
    reason_code = result.get("reason_code")
    if reason_code not in REASON_CODES:
        raise ValueError(f"{location}.reason_code invalid")
    explanation = result.get("explanation")
    if not isinstance(explanation, str) or not 8 <= len(explanation.split()) <= 60:
        raise ValueError(f"{location}.explanation must contain 8-60 words")
    evidence = result.get("evidence")
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= 3:
        raise ValueError(f"{location}.evidence must contain 1-3 anchors")
    fingerprints: list[str] = []
    quote_present = pointer_present = False
    for index, anchor in enumerate(evidence):
        if not isinstance(anchor, dict):
            raise ValueError(f"{location}.evidence[{index}] must be an object")
        kind = anchor.get("kind")
        if kind == "answer_quote":
            quote = anchor.get("quote")
            if not isinstance(quote, str) or not 3 <= len(quote.split()) <= 40:
                raise ValueError(f"{location}.evidence[{index}].quote must contain 3-40 words")
            if quote not in bundle["answer"]:
                raise ValueError(f"{location}.evidence[{index}].quote is not in answer")
            if quote.casefold() not in explanation.casefold():
                raise ValueError(f"{location}.explanation must cite its answer quote")
            quote_present = True
            fingerprints.append(f"q:{quote.casefold()}")
        elif kind == "context_pointer":
            pointer = anchor.get("pointer")
            observed = anchor.get("observed_value")
            actual = _pointer_get({"context": bundle["context"]}, pointer)
            if observed != actual:
                raise ValueError(f"{location}.evidence[{index}].observed_value mismatch")
            if pointer not in explanation:
                raise ValueError(f"{location}.explanation must cite its context pointer")
            pointer_present = True
            fingerprints.append(f"p:{pointer}:{canonical_json(observed)}")
        else:
            raise ValueError(f"{location}.evidence[{index}].kind invalid")
    if reason_code in {"contradicted", "field_misread", "false_comparison"}:
        if not quote_present or not pointer_present:
            raise ValueError(f"{location} contradiction requires quote and context pointer")
    if len(fingerprints) != len(set(fingerprints)):
        raise ValueError(f"{location}.evidence contains duplicate anchors")
    lowered = explanation.casefold().strip(" .")
    if lowered in GENERIC_EXPLANATIONS:
        raise ValueError(f"{location}.explanation is generic")
    return _normalize_explanation(explanation, evidence), tuple(sorted(fingerprints))


def validate_verdict(
    verdict: dict[str, Any], bundle: dict[str, Any], location: str
) -> tuple[list[tuple[str, str]], list[tuple[str, tuple[str, ...]]]]:
    if verdict.get("example_id") != bundle.get("example_id"):
        raise ValueError(f"{location} example_id mismatch")
    validate_stamp(verdict, bundle, location)
    for key in ("qualification_pack_sha256", "calibration_sha256", "bundle_sha256"):
        if verdict.get(key) != bundle.get(key):
            raise ValueError(f"{location} {key} mismatch")
    for key in ("run_id", "session_id", "shard_id"):
        if bundle.get(key) is not None and verdict.get(key) != bundle.get(key):
            raise ValueError(f"{location} {key} mismatch")
    judge = verdict.get("judge")
    if not isinstance(judge, str) or not judge:
        raise ValueError(f"{location} judge must be non-empty")
    criteria = verdict.get("criteria")
    if not isinstance(criteria, dict):
        raise ValueError(f"{location}.criteria must be an object")
    required = set(bundle["expected_criteria"])
    if set(criteria) != required:
        raise ValueError(f"{location} criterion coverage mismatch")
    explanations: list[tuple[str, str]] = []
    anchors: list[tuple[str, tuple[str, ...]]] = []
    for criterion_id, result in criteria.items():
        if not isinstance(result, dict) or not isinstance(result.get("pass"), bool):
            raise ValueError(f"{location}.{criterion_id}.pass must be boolean")
        if result["pass"]:
            if set(result) - {"pass", "explanation"}:
                raise ValueError(f"{location}.{criterion_id} pass result has extra fields")
        else:
            fingerprint, evidence_fingerprint = validate_failure_result(
                result, bundle, f"{location}.{criterion_id}"
            )
            explanations.append((criterion_id, fingerprint))
            anchors.append((criterion_id, evidence_fingerprint))
    category_ids = CATEGORY_CRITERIA[bundle["task_category"]]
    derived = all(criteria[criterion_id]["pass"] for criterion_id in category_ids)
    if verdict.get("category_pass") is not derived:
        raise ValueError(f"{location} category_pass must equal category AND={derived}")
    return explanations, anchors


def validate_batch(
    verdicts: dict[str, dict[str, Any]], bundles: dict[str, dict[str, Any]], location: str
) -> dict[str, Any]:
    if set(verdicts) != set(bundles):
        raise ValueError(f"{location} coverage mismatch")
    explanation_counts: Counter[tuple[str, str]] = Counter()
    anchor_counts: Counter[tuple[str, tuple[str, ...]]] = Counter()
    pass_counts: dict[str, list[bool]] = defaultdict(list)
    for example_id, verdict in verdicts.items():
        explanations, anchors = validate_verdict(verdict, bundles[example_id], f"{location}:{example_id}")
        explanation_counts.update(explanations)
        anchor_counts.update(anchors)
        for criterion_id, result in verdict["criteria"].items():
            pass_counts[criterion_id].append(result["pass"])
    repeated_explanations = [key for key, count in explanation_counts.items() if count >= 3]
    if repeated_explanations:
        raise ValueError(f"{location} repeated generic failure explanations: {repeated_explanations[:3]}")
    repeated_anchors = [key for key, count in anchor_counts.items() if count >= 3]
    if repeated_anchors:
        raise ValueError(f"{location} reused failure evidence: {repeated_anchors[:3]}")
    all_fail = [criterion_id for criterion_id, values in pass_counts.items() if len(values) >= 8 and not any(values)]
    if all_fail:
        raise ValueError(f"{location} degenerate all-fail criteria: {all_fail}")
    return {
        "count": len(verdicts),
        "failure_explanation_fingerprints": len(explanation_counts),
        "failure_evidence_fingerprints": len(anchor_counts),
        "all_fail_criteria": [],
    }


def agreement_stats(a: dict[str, dict[str, Any]], b: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if set(a) != set(b):
        raise ValueError("agreement coverage differs")
    n = len(a)
    both_pass = both_fail = a_pass_b_fail = a_fail_b_pass = 0
    criterion_same = criterion_total = 0
    for example_id in a:
        av, bv = bool(a[example_id]["category_pass"]), bool(b[example_id]["category_pass"])
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
    kappa = None if expected >= 1.0 else (agreement - expected) / (1 - expected)
    return {
        "count": n,
        "raw_category_agreement_rate": agreement,
        "raw_pass_rate_gap": abs(a_rate - b_rate),
        "raw_cohen_kappa": kappa,
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


def trust_result(stats: dict[str, Any]) -> dict[str, Any]:
    agreement = stats.get("raw_category_agreement_rate", stats["category_agreement_rate"])
    kappa = stats.get("raw_cohen_kappa", stats["cohen_kappa"])
    gap = stats.get("raw_pass_rate_gap", stats["pass_rate_gap"])
    failures: list[str] = []
    if agreement < TRUST_THRESHOLDS["category_agreement_rate"]:
        failures.append("category_agreement_rate")
    if kappa is None or kappa < TRUST_THRESHOLDS["cohen_kappa"]:
        failures.append("cohen_kappa")
    if gap > TRUST_THRESHOLDS["pass_rate_gap"]:
        failures.append("pass_rate_gap")
    return {"trusted": not failures, "failures": failures, "thresholds": TRUST_THRESHOLDS}


def validate_agreement_stats(stats: dict[str, Any], expected_count: int = 200) -> dict[str, Any]:
    """Reconstruct gate metrics from integer confusion counts, never asserted floats."""
    count = stats.get("count")
    confusion = stats.get("category_confusion")
    keys = {"both_pass", "both_fail", "a_pass_b_fail", "a_fail_b_pass"}
    if count != expected_count or not isinstance(confusion, dict) or set(confusion) != keys:
        raise ValueError(f"trust statistics must contain exactly {expected_count} paired rows")
    if any(not isinstance(confusion[key], int) or confusion[key] < 0 for key in keys):
        raise ValueError("trust confusion counts must be non-negative integers")
    if sum(confusion.values()) != count:
        raise ValueError("trust confusion counts do not sum to count")
    both_pass = confusion["both_pass"]
    both_fail = confusion["both_fail"]
    a_pass_b_fail = confusion["a_pass_b_fail"]
    a_fail_b_pass = confusion["a_fail_b_pass"]
    agreement = (both_pass + both_fail) / count
    a_rate = (both_pass + a_pass_b_fail) / count
    b_rate = (both_pass + a_fail_b_pass) / count
    expected = a_rate * b_rate + (1 - a_rate) * (1 - b_rate)
    kappa = None if expected >= 1.0 else (agreement - expected) / (1 - expected)
    recomputed = {
        "raw_category_agreement_rate": agreement,
        "raw_pass_rate_gap": abs(a_rate - b_rate),
        "raw_cohen_kappa": kappa,
        "category_agreement_count": both_pass + both_fail,
        "category_agreement_rate": round(agreement, 4),
        "pass_a_rate": round(a_rate, 4),
        "pass_b_rate": round(b_rate, 4),
        "pass_rate_gap": round(abs(a_rate - b_rate), 4),
        "cohen_kappa": None if kappa is None else round(kappa, 4),
    }
    for key, expected_value in recomputed.items():
        actual = stats.get(key)
        if isinstance(expected_value, float):
            if not isinstance(actual, (int, float)) or not math.isclose(
                float(actual), expected_value, rel_tol=0.0, abs_tol=1e-12
            ):
                raise ValueError(f"trust statistic {key} does not match confusion counts")
        elif actual != expected_value:
            raise ValueError(f"trust statistic {key} does not match confusion counts")
    return {**recomputed, "count": count, "category_confusion": confusion}


def reject_asymmetric_constant_pass(
    a: dict[str, dict[str, Any]], b: dict[str, dict[str, Any]], location: str
) -> None:
    """Reject one-sided blanket passing when its paired judge finds repeated failures."""
    for left_name, left, right in (("a", a, b), ("b", b, a)):
        exposures: dict[str, list[bool]] = defaultdict(list)
        paired: dict[str, list[bool]] = defaultdict(list)
        for example_id, verdict in left.items():
            for criterion_id, result in verdict["criteria"].items():
                exposures[criterion_id].append(result["pass"])
                paired[criterion_id].append(right[example_id]["criteria"][criterion_id]["pass"])
        degenerate = [
            criterion_id for criterion_id, values in exposures.items()
            if len(values) >= 8 and all(values) and sum(not value for value in paired[criterion_id]) >= 3
        ]
        if degenerate:
            raise ValueError(
                f"{location} session-{left_name} degenerate all-pass criteria: {degenerate}"
            )


def validate_trust_receipt(receipt: dict[str, Any], system: str) -> dict[str, Any]:
    """Fail closed on a v2 trust receipt before any downstream verdict work."""
    recorded_hash = receipt.get("receipt_sha256")
    payload = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    if not isinstance(recorded_hash, str) or recorded_hash != sha256_json(payload):
        raise ValueError("trust receipt SHA-256 is invalid")
    if receipt.get("judge_protocol_version") != JUDGE_PROTOCOL_VERSION:
        raise ValueError("trust receipt protocol mismatch")
    if receipt.get("qualification_pack_sha256") != qualification_pack_sha256():
        raise ValueError("trust receipt qualification pack mismatch")
    if not isinstance(receipt.get("run_id"), str) or not receipt["run_id"]:
        raise ValueError("trust receipt run_id is missing")
    def require_sha(value: Any, location: str) -> None:
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"trust receipt {location} must be a SHA-256")
    require_sha(receipt.get("manifest_sha256"), "manifest_sha256")
    require_sha(receipt.get("trust_report_sha256"), "trust_report_sha256")
    for label in ("ft_v2", "candidate"):
        require_sha(receipt.get("source_bundle_sha256", {}).get(label), f"source_bundle_sha256.{label}")
    for session in ("session-a", "session-b"):
        require_sha(
            receipt.get("qualification_receipt_sha256", {}).get(session),
            f"qualification_receipt_sha256.{session}",
        )
    for label in ("ft_v2", "candidate"):
        for session in ("session-a", "session-b"):
            require_sha(
                receipt.get("primary_output_sha256", {}).get(label, {}).get(session),
                f"primary_output_sha256.{label}.{session}",
            )
    systems = receipt.get("systems")
    if not isinstance(systems, dict) or set(systems) != {"ft_v2", "candidate"} or system not in systems:
        raise ValueError(f"trust receipt has no system {system!r}")
    report = systems[system]
    validate_agreement_stats(report)
    recomputed = trust_result(report)
    if report.get("trusted") is not recomputed["trusted"] or report.get("failures") != recomputed["failures"]:
        raise ValueError("trust receipt system result does not match its statistics")
    expected_overall = True
    for value in systems.values():
        if not isinstance(value, dict):
            raise ValueError("trust receipt system report must be an object")
        validate_agreement_stats(value)
        expected_overall = expected_overall and trust_result(value)["trusted"]
    if receipt.get("overall_trusted") is not expected_overall or not expected_overall:
        raise ValueError("trust receipt is not trusted for every system")
    return report
