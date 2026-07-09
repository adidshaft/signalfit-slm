#!/usr/bin/env python3
"""One-command frozen-suite check for a local SignalFit adapter.

This runs only local/free steps:
  1. freeze_eval check
  2. generate_answers over eval/v1 core + adversarial + binding slices
  3. run_eval deterministic gates + judge bundle

If you already have independent judge verdicts, pass --verdicts to also build a
judged_report.json and run check_regression.py against the pinned baseline.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
PY = REPO / ".venv" / "bin" / "python"
DEFAULT_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
DEFAULT_ADAPTER = "models/adapters/ft_v2_qwen2.5-1.5b"
CASE_DIRS = ["eval/v1/cases/core", "eval/v1/cases/adversarial", "eval/v1/cases/binding"]


def run(cmd: list[str], *, allow_fail: bool = False) -> subprocess.CompletedProcess:
    print("\n$ " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=REPO)
    if result.returncode and not allow_fail:
        raise SystemExit(result.returncode)
    return result


def default_out_dir(adapter: str) -> Path:
    name = Path(adapter).name or "model"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return REPO / "data" / "checks" / f"{name}-{stamp}"


def print_summary(report_path: Path) -> None:
    report = json.loads(report_path.read_text())
    summary = report["summary"]
    triple = (
        "sf-eval-v1",
        summary["gate_version"],
        summary["rubric_version"],
    )
    print("\nSummary")
    print(f"  triple: {triple}")
    print(f"  count: {summary['count']}")
    print(f"  deterministic_pass_rate: {summary['deterministic_pass_rate']}")
    if "overall_pass_rate" in summary:
        print(f"  judge_category_pass_rate: {summary['judge_category_pass_rate']}")
        print(f"  overall_pass_rate: {summary['overall_pass_rate']}")
    print("  by_gate:")
    for gate, item in summary["by_gate"].items():
        print(f"    {gate}: {item['pass']}/{item['n']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", default=DEFAULT_ADAPTER,
                        help=f"adapter path (default: {DEFAULT_ADAPTER})")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"base model id/path (default: {DEFAULT_MODEL})")
    parser.add_argument("--out-dir", default=None,
                        help="output directory; defaults to data/checks/<adapter>-timestamp")
    parser.add_argument("--max-tokens", type=int, default=350)
    parser.add_argument("--verdicts", default=None,
                        help="optional judge verdict JSONL to apply after deterministic eval")
    parser.add_argument("--baseline", default="eval/v1/baseline/ft_v2.judged_report.json")
    parser.add_argument("--skip-regression", action="store_true",
                        help="with --verdicts, build judged report but do not run check_regression")
    args = parser.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else default_out_dir(args.adapter)
    out_dir.mkdir(parents=True, exist_ok=True)
    generations = out_dir / "suite_generations.jsonl"
    eval_dir = out_dir / "eval_report"
    judged_report = eval_dir / "judged_report.json"

    run([str(PY), "scripts/freeze_eval.py", "check", "--version", "v1"])
    run([
        str(PY), "scripts/generate_answers.py",
        "--examples", *CASE_DIRS,
        "--model", args.model,
        "--adapter", args.adapter,
        "--max-tokens", str(args.max_tokens),
        "-o", str(generations),
    ])
    run([
        str(PY), "scripts/run_eval.py",
        "--examples", "eval/v1/cases",
        "--generations", str(generations),
        "--out-dir", str(eval_dir),
    ])
    print_summary(eval_dir / "eval_report.json")

    print("\nJudge bundle:")
    print(f"  {eval_dir / 'judge_bundle.jsonl'}")
    print("  For the full judged workflow, create two independent judge passes,")
    print("  merge/adjudicate them, then rerun this script with --verdicts <final.jsonl>.")

    if args.verdicts:
        run([
            str(PY), "scripts/apply_judge.py",
            "--report", str(eval_dir / "eval_report.json"),
            "--verdicts", args.verdicts,
            "--out", str(judged_report),
        ])
        print_summary(judged_report)
        if not args.skip_regression:
            regression = run([
                str(PY), "scripts/check_regression.py",
                "--baseline", args.baseline,
                "--candidate", str(judged_report),
            ], allow_fail=True)
            return regression.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
