#!/usr/bin/env python3
"""Summarize a full verify/retry system run and named protect-case outcomes."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any


def _jsonl_by_id(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        example_id = row.get("example_id")
        if not isinstance(example_id, str) or not example_id:
            raise ValueError(f"{path}:{line_no} has no string example_id")
        if example_id in rows:
            raise ValueError(f"{path} has duplicate example_id {example_id!r}")
        rows[example_id] = row
    return rows


def _report_by_id(path: Path) -> dict[str, dict[str, Any]]:
    report = json.loads(path.read_text())
    rows: dict[str, dict[str, Any]] = {}
    for row in report.get("results", []):
        example_id = row.get("example_id")
        if not isinstance(example_id, str) or example_id in rows:
            raise ValueError(f"{path} has invalid or duplicate example_id")
        rows[example_id] = row
    if not rows:
        raise ValueError(f"{path} has no results")
    return rows


def _number(value: Any, location: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{location} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{location} must be a finite non-negative number")
    return result


def _percentile(values: list[float], fraction: float) -> float | None:
    """Linear percentile over sorted observations using index (n - 1) * p."""
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _stats(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "median_ms": round(statistics.median(values), 1) if values else None,
        "p95_ms": round(_percentile(values, 0.95), 1) if values else None,
        "percentile_method": "linear interpolation at (n-1)*p",
    }


def summarize(
    logs: dict[str, dict[str, Any]],
    current: dict[str, dict[str, Any]],
    previous: dict[str, dict[str, Any]],
    protected_ids: list[str],
) -> dict[str, Any]:
    if set(logs) != set(current):
        raise ValueError("correction-log and eval-report ID coverage differ")
    if set(previous) != set(current):
        raise ValueError("previous and current eval-report ID coverage differ")

    draft_latencies: list[float] = []
    retry_latencies: list[float] = []
    total_latencies: list[float] = []
    retry_count = 0
    retry2_count = 0
    directive_fire_count = 0
    for example_id, row in logs.items():
        draft = _number(row.get("draft_latency_ms"), f"{example_id}.draft_latency_ms")
        draft_latencies.append(draft)
        total = draft
        if row.get("retry_triggered"):
            retry_count += 1
            retry = _number(row.get("retry_latency_ms"), f"{example_id}.retry_latency_ms")
            retry_latencies.append(retry)
            total += retry
        if row.get("retry2_triggered"):
            retry2_count += 1
            total += _number(
                row.get("retry2_latency_ms"), f"{example_id}.retry2_latency_ms"
            )
        directive_fire_count += int(bool(row.get("directive_fired")))
        total_latencies.append(total)

    protected: dict[str, Any] = {}
    for example_id in protected_ids:
        if example_id not in current:
            raise ValueError(f"protected ID {example_id!r} is absent")
        log = logs[example_id]
        old_pass = previous[example_id].get("deterministic_pass")
        new_pass = current[example_id].get("deterministic_pass")
        protected[example_id] = {
            "previous_deterministic_pass": old_pass,
            "current_deterministic_pass": new_pass,
            "flipped_fail_to_pass": old_pass is False and new_pass is True,
            "retry_triggered": bool(log.get("retry_triggered")),
            "draft_failed_checks": sorted(log.get("failures", {})),
            "final_wrapper_checks_pass": bool(log.get("final_answer_side_pass")),
            "final_eval_failed_gates": sorted(
                name
                for name, outcome in current[example_id].get("checks", {}).items()
                if not outcome.get("pass")
            ),
        }

    n = len(logs)
    return {
        "count": n,
        "retry_count": retry_count,
        "retry_rate": round(retry_count / n, 4) if n else None,
        "retry2_count": retry2_count,
        "directive_fire_count": directive_fire_count,
        "directive_fire_rate": round(directive_fire_count / n, 4) if n else None,
        "latency": {
            "draft_all_cases": _stats(draft_latencies),
            "retry_retried_cases_only": _stats(retry_latencies),
            "total_system_all_cases": _stats(total_latencies),
        },
        "protected_cases": protected,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--correction-log", type=Path, required=True)
    parser.add_argument("--eval-report", type=Path, required=True)
    parser.add_argument("--previous-report", type=Path, required=True)
    parser.add_argument("--protected-id", action="append", default=[])
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    try:
        result = summarize(
            _jsonl_by_id(args.correction_log),
            _report_by_id(args.eval_report),
            _report_by_id(args.previous_report),
            args.protected_id,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered)
        print(f"summary -> {args.out}")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
