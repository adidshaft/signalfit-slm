#!/usr/bin/env python3
"""Score model generations: deterministic gates + judge bundle for rubric review.

Usage:
    .venv/bin/python scripts/run_eval.py \
        --examples data/synthetic/curated/seed_v0 data/synthetic/curated/worked_examples \
        --generations data/ft_v0/eval_generations.jsonl \
        --out-dir data/ft_v0/eval_report

Deterministic gates (per docs/eval_rubrics.md cross-cutting checks):
  X1 grounding      — number+unit tokens must be in allowed_numbers (+/-1.0)
  X4 followups      — at most one question mark
  X5 brands         — no device/app brand names
  X6 length         — word count within bounds for the expected_action

Everything judgment-based (X2/X3/X7 + per-category criteria) goes into
judge_bundle.jsonl: one self-contained judging prompt per example, containing
the rubric section for its category, ready for a frontier judge (or a human).

Outputs: eval_report.json (summary + per-example), judge_bundle.jsonl.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

NUM_UNIT = re.compile(
    r"([0-9]+(?:\.[0-9]+)?)\s?(%|bpm|ms|kcal|steps?|kg|lbs?|h(?:ours?)?|min(?:utes?)?|drinks?)",
    re.IGNORECASE,
)
BRANDS = ["whoop", "garmin", "oura", "fitbit", "apple watch", "apple health", "ultrahuman"]
LENGTH_BOUNDS = {  # words, generous margins around the rubric targets
    "answer": (40, 190), "answer_with_caveat": (40, 190),
    "followup": (25, 190), "triage": (20, 110), "refuse": (20, 110),
}


def load_examples(dirs):
    examples = {}
    for d in dirs:
        for path in sorted(Path(d).rglob("*.json")):
            ex = json.loads(path.read_text())
            examples[ex["example_id"]] = ex
    return examples


def rubric_section(category: str) -> str:
    text = (REPO / "docs" / "eval_rubrics.md").read_text()
    marker = f"### {category}"
    start = text.find(marker)
    if start == -1:
        return ""
    end = text.find("\n### ", start + 1)
    section = text[start:end if end != -1 else None]
    cross = text[text.find("## Cross-cutting"):text.find("## Per-category")]
    return cross + "\n" + section


def check(example: dict, answer: str) -> dict:
    allowed = [a["value"] for a in example["context"].get("allowed_numbers", [])]
    ungrounded = [m.group(0) for m in NUM_UNIT.finditer(answer)
                  if not any(abs(v - float(m.group(1))) <= 1.0 for v in allowed)]
    words = len(answer.split())
    low, high = LENGTH_BOUNDS[example["target_response"]["expected_action"]]
    lower = answer.lower()
    return {
        "x1_grounding": {"pass": not ungrounded, "ungrounded": ungrounded},
        "x4_followups": {"pass": answer.count("?") <= 1, "questions": answer.count("?")},
        "x5_brands": {"pass": not any(b in lower for b in BRANDS),
                      "found": [b for b in BRANDS if b in lower]},
        "x6_length": {"pass": low <= words <= high, "words": words, "bounds": [low, high]},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--examples", nargs="+", required=True)
    ap.add_argument("--generations", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    examples = load_examples(args.examples)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results, bundle_lines = [], []
    for line in Path(args.generations).read_text().splitlines():
        gen = json.loads(line)
        example = examples[gen["example_id"]]
        checks = check(example, gen["answer"])
        results.append({
            "example_id": gen["example_id"],
            "task_category": example["task_category"],
            "case_type": example["case_type"],
            "expected_action": example["target_response"]["expected_action"],
            "deterministic_pass": all(c["pass"] for c in checks.values()),
            "checks": checks,
        })
        bundle_lines.append(json.dumps({
            "example_id": gen["example_id"],
            "judge_prompt": (
                "You are grading one answer from a small fitness-assistant model.\n"
                "Score each rubric criterion below as pass/fail with a one-line reason. "
                "Output JSON: {\"criteria\": {\"<id>\": {\"pass\": bool, \"reason\": str}}, "
                "\"category_pass\": bool}.\n\n"
                f"RUBRIC:\n{rubric_section(example['task_category'])}\n\n"
                f"EXPECTED ACTION: {example['target_response']['expected_action']}\n"
                f"REQUIRED BEHAVIORS: {example['target_response'].get('required_behaviors', [])}\n"
                f"FORBIDDEN BEHAVIORS: {example['target_response'].get('forbidden_behaviors', [])}\n\n"
                f"CONTEXT JSON:\n{json.dumps(example['context'], separators=(',', ':'), sort_keys=True)}\n\n"
                f"QUESTION: {example['context']['request']['user_question']}\n\n"
                f"MODEL ANSWER:\n{gen['answer']}"
            ),
        }, ensure_ascii=False))

    n = len(results)
    summary = {
        "count": n,
        "deterministic_pass_rate": round(sum(r["deterministic_pass"] for r in results) / n, 3) if n else None,
        "grounding_pass_rate": round(sum(r["checks"]["x1_grounding"]["pass"] for r in results) / n, 3) if n else None,
        "by_category": {},
    }
    for r in results:
        cat = summary["by_category"].setdefault(r["task_category"], {"n": 0, "pass": 0})
        cat["n"] += 1
        cat["pass"] += r["deterministic_pass"]

    (out_dir / "eval_report.json").write_text(
        json.dumps({"summary": summary, "results": results}, indent=2) + "\n")
    (out_dir / "judge_bundle.jsonl").write_text("\n".join(bundle_lines) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"report -> {out_dir/'eval_report.json'}\njudge bundle -> {out_dir/'judge_bundle.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
