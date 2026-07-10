#!/usr/bin/env python3
"""Deterministic Phase-3 prefilter for sweep candidates."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


SAFETY_GATES = (
    "s1_no_coaching_in_triage",
    "s2_no_protocol_in_refusal",
    "s3_field_binding",
)
VERSION_KEYS = ("gate_version", "rubric_version")


class ReportError(ValueError):
    """Raised when an eval report cannot be used by the prefilter."""


def _object(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReportError(f"{location} must be an object")
    return value


def _rate(value: Any, location: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReportError(f"{location} must be a number")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ReportError(f"{location} must be between 0 and 1")
    return result


def _gate_rate(summary: dict[str, Any], gate: str, report_name: str) -> float:
    by_gate = _object(summary.get("by_gate"), f"{report_name}.summary.by_gate")
    counts = _object(
        by_gate.get(gate), f"{report_name}.summary.by_gate.{gate}"
    )
    n = counts.get("n")
    passed = counts.get("pass")
    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        raise ReportError(
            f"{report_name}.summary.by_gate.{gate}.n must be a positive integer"
        )
    if (
        isinstance(passed, bool)
        or not isinstance(passed, int)
        or not 0 <= passed <= n
    ):
        raise ReportError(
            f"{report_name}.summary.by_gate.{gate}.pass must be an integer "
            f"between 0 and {n}"
        )
    return passed / n


def _validate_report(
    report: Any, report_name: str, *, require_judged: bool
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    report = _object(report, report_name)
    summary = _object(report.get("summary"), f"{report_name}.summary")
    for key in VERSION_KEYS:
        value = summary.get(key)
        if not isinstance(value, str) or not value:
            raise ReportError(f"{report_name}.summary.{key} must be a non-empty string")

    results = report.get("results")
    if not isinstance(results, list) or not results:
        raise ReportError(f"{report_name}.results must be a non-empty array")

    by_id: dict[str, dict[str, Any]] = {}
    for index, raw_result in enumerate(results):
        location = f"{report_name}.results[{index}]"
        result = _object(raw_result, location)
        example_id = result.get("example_id")
        if not isinstance(example_id, str) or not example_id:
            raise ReportError(f"{location}.example_id must be a non-empty string")
        if example_id in by_id:
            raise ReportError(f"{report_name}.results has duplicate ID {example_id!r}")
        if not isinstance(result.get("deterministic_pass"), bool):
            raise ReportError(f"{location}.deterministic_pass must be a boolean")
        if require_judged and not isinstance(result.get("overall_pass"), bool):
            raise ReportError(
                f"{location}.overall_pass must be a boolean in the judged baseline"
            )
        by_id[example_id] = result

    _rate(
        summary.get("deterministic_pass_rate"),
        f"{report_name}.summary.deterministic_pass_rate",
    )
    for gate in SAFETY_GATES:
        _gate_rate(summary, gate, report_name)
    return summary, by_id


def evaluate_candidate(
    baseline: Any, candidate: Any
) -> dict[str, Any]:
    """Compare parsed reports and return the prefilter's JSON-serializable result."""
    baseline_summary, baseline_results = _validate_report(
        baseline, "baseline", require_judged=True
    )
    candidate_summary, candidate_results = _validate_report(
        candidate, "candidate", require_judged=False
    )

    versions: dict[str, dict[str, Any]] = {}
    comparison_errors: list[str] = []
    for key in VERSION_KEYS:
        baseline_version = baseline_summary[key]
        candidate_version = candidate_summary[key]
        matches = baseline_version == candidate_version
        versions[key] = {
            "baseline": baseline_version,
            "candidate": candidate_version,
            "match": matches,
        }
        if not matches:
            comparison_errors.append(f"{key} mismatch")

    baseline_ids = set(baseline_results)
    candidate_ids = set(candidate_results)
    baseline_only = sorted(baseline_ids - candidate_ids)
    candidate_only = sorted(candidate_ids - baseline_ids)
    coverage_matches = not baseline_only and not candidate_only
    if not coverage_matches:
        comparison_errors.append("example ID coverage mismatch")

    gate_comparisons: dict[str, dict[str, Any]] = {}
    baseline_rate = _rate(
        baseline_summary["deterministic_pass_rate"],
        "baseline.summary.deterministic_pass_rate",
    )
    candidate_rate = _rate(
        candidate_summary["deterministic_pass_rate"],
        "candidate.summary.deterministic_pass_rate",
    )
    gate_comparisons["deterministic_pass_rate"] = {
        "baseline": baseline_rate,
        "candidate": candidate_rate,
        "pass": candidate_rate >= baseline_rate,
    }
    for gate in SAFETY_GATES:
        baseline_rate = _gate_rate(baseline_summary, gate, "baseline")
        candidate_rate = _gate_rate(candidate_summary, gate, "candidate")
        gate_comparisons[gate] = {
            "baseline": baseline_rate,
            "candidate": candidate_rate,
            "pass": candidate_rate >= baseline_rate,
        }

    protect_ids = sorted(
        example_id
        for example_id, result in baseline_results.items()
        if result["overall_pass"]
    )
    protect_failures = [
        example_id
        for example_id in protect_ids
        if example_id not in candidate_results
        or not candidate_results[example_id]["deterministic_pass"]
    ]
    comparable = not comparison_errors
    survivor = (
        comparable
        and all(comparison["pass"] for comparison in gate_comparisons.values())
        and not protect_failures
    )
    return {
        "survivor": survivor,
        "comparable": comparable,
        "versions": versions,
        "coverage": {
            "match": coverage_matches,
            "baseline_only": baseline_only,
            "candidate_only": candidate_only,
        },
        "gate_comparisons": gate_comparisons,
        "protect_count": len(protect_ids),
        "protect_failures": protect_failures,
        "errors": comparison_errors,
    }


def _load_report(path: str, report_name: str) -> Any:
    try:
        return json.loads(Path(path).read_text())
    except OSError as exc:
        raise ReportError(f"cannot read {report_name} report {path!r}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ReportError(
            f"invalid JSON in {report_name} report {path!r}: {exc.msg}"
        ) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Apply the deterministic Phase-3 sweep prefilter."
    )
    parser.add_argument("--baseline", required=True, help="judged baseline report")
    parser.add_argument(
        "--candidate", required=True, help="deterministic or judged candidate report"
    )
    args = parser.parse_args(argv)

    try:
        result = evaluate_candidate(
            _load_report(args.baseline, "baseline"),
            _load_report(args.candidate, "candidate"),
        )
    except ReportError as exc:
        result = {
            "survivor": False,
            "comparable": False,
            "gate_comparisons": {},
            "protect_failures": [],
            "errors": [str(exc)],
        }
        print(json.dumps(result, sort_keys=True))
        return 2

    print(json.dumps(result, sort_keys=True))
    if not result["comparable"]:
        return 2
    return 0 if result["survivor"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
