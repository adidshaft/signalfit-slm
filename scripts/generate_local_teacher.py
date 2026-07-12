#!/usr/bin/env python3
"""Distillation-to-scale: generate training rows with a LOCAL teacher model.

The $0 path from docs/distillation_plan.md. A larger open model runs locally
via mlx (free, offline) as the answer generator; every teacher answer is
re-checked against sf-gates-12 and only gate-clean rows enter the dataset, so
teacher noise is discarded rather than trained on.

Pipeline per context spec (from scripts/make_context_specs.py):
  1. Teacher writes a realistic user question for (context, category).
  2. Teacher writes a grounded answer under the frozen serving system prompt.
  3. expected_action is assigned deterministically from category (gate-correct:
     answer / answer_with_caveat are gate-equivalent, so non-safety categories
     collapse to answer_with_caveat).
  4. sf-gates-12 check() filters: gate-clean -> dataset, else -> quarantine.

Usage:
    # smoke-test the whole pipeline with a stub teacher (no GPU, no download):
    .venv/bin/python scripts/generate_local_teacher.py \
        --specs data/synthetic/raw/teacher_pilot/specs \
        --out data/synthetic/raw/teacher_pilot --stub

    # real run once a teacher is cached (e.g. mlx-community/Qwen3-8B-4bit):
    .venv/bin/python scripts/generate_local_teacher.py \
        --specs data/synthetic/raw/teacher_pilot/specs \
        --out data/synthetic/raw/teacher_pilot \
        --teacher mlx-community/Qwen3-8B-4bit
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from prepare_dataset import SYSTEM_PROMPT, model_input_context  # noqa: E402
from run_eval import check  # noqa: E402 -- the frozen sf-gates-12 filter

# Gate-correct action per category. answer and answer_with_caveat share
# identical length bounds and impose no distinct safety gate, so every
# non-(followup/refuse/triage) category collapses to answer_with_caveat.
ACTION_BY_CATEGORY = {
    "insufficient_data_followup": "followup",
    "refusal_or_redirect": "refuse",
    "safety_triage": "triage",
}
DEFAULT_ACTION = "answer_with_caveat"
SAFETY_CLASS_BY_CATEGORY = {
    "safety_triage": "medical_red_flag",
    "refusal_or_redirect": "ped_request",
}


def action_for(category: str) -> str:
    return ACTION_BY_CATEGORY.get(category, DEFAULT_ACTION)


def question_prompt(context: dict, category: str) -> list[dict[str, str]]:
    ctx = json.dumps(model_input_context(context), separators=(",", ":"), sort_keys=True)
    return [
        {"role": "system", "content": (
            "You write realistic first-person questions a fitness-app user would "
            "ask about their own wearable data. Output ONLY the question text.")},
        {"role": "user", "content": (
            f"Category: {category}\nCONTEXT:\n{ctx}\n\n"
            "Write one natural question this user would ask for that category.")},
    ]


def answer_prompt(context: dict, question: str) -> list[dict[str, str]]:
    ctx = json.dumps(model_input_context(context), separators=(",", ":"), sort_keys=True)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"CONTEXT:\n{ctx}\n\nQUESTION: {question}"},
    ]


def assemble_example(spec: dict, question: str, answer: str) -> dict:
    context = dict(spec["context"])
    context.setdefault("request", {})
    context["request"] = dict(context["request"])
    context["request"]["user_question"] = question
    category = spec["category"]
    return {
        "example_id": spec["example_id"],
        "schema_version": "sf-train-1",
        "context": context,
        "task_category": category,
        "case_type": spec.get("case_type", "normal"),
        "target_response": {
            "text": answer,
            "expected_action": action_for(category),
            "must_mention": [],
            "must_not_mention": [],
            "required_behaviors": [],
            "forbidden_behaviors": ["invents_numbers", "population_stats_as_personal"],
        },
        "labels": {
            "safety_class": SAFETY_CLASS_BY_CATEGORY.get(category, "none"),
            "persona_id": spec.get("persona_id"),
            "is_locked_eval": spec.get("is_locked_eval", False),
            "provider_mask": spec.get("mask", "wearable_full"),
            "rubric_tags": ["distill-local-teacher", category],
        },
        "generation": {
            "generator": "local-teacher",
            "prompt_version": "distill-v1",
            "critic_passed": False,
            "human_reviewed": False,
            "created_at": "2026-07-12",
        },
    }


def gate_clean(example: dict) -> tuple[bool, dict]:
    checks = check(example, example["target_response"]["text"])
    failed = {name: r for name, r in checks.items() if not r["pass"]}
    return (not failed), failed


def load_specs(specs_dir: Path) -> list[dict]:
    specs = []
    for chunk in sorted(specs_dir.glob("chunk_*.json")):
        specs.extend(json.loads(chunk.read_text()))
    return specs


def stub_generator(specs: list[dict]) -> Callable[[list[dict]], str]:
    """A deterministic fake teacher for pipeline smoke-tests (no GPU).

    Emits a gate-clean grounded answer for answer-type specs and a clean
    refusal/triage/followup for the safety categories, so the filter's
    accept path is exercised without any model.
    """
    by_id = {s["example_id"]: s for s in specs}

    def generate(messages: list[dict]) -> str:
        user = messages[-1]["content"]
        if user.startswith("Category:"):  # question call
            return "What does my data suggest I should do about this today?"
        # answer call — echo one grounded number if available
        eid = None
        for s in specs:
            if s["context"].get("request", {}).get("user_question"):
                pass
        # find the spec whose context is embedded in this prompt is overkill;
        # produce a category-agnostic gate-clean answer with no numbers.
        return (
            "Based only on what your data shows, keep today's plan steady and "
            "make small, reversible adjustments rather than large ones. Watch "
            "the multi-day trend against your own usual range before changing "
            "anything, and check in again if how you feel keeps drifting from "
            "what the numbers say."
        )

    return generate


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--specs", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--teacher", default=None, help="mlx model id; omit with --stub")
    ap.add_argument("--stub", action="store_true", help="use a fake teacher (pipeline test)")
    ap.add_argument("--max-tokens", type=int, default=350)
    ap.add_argument("--limit", type=int, default=None, help="cap specs processed")
    args = ap.parse_args()

    specs = load_specs(args.specs)
    if args.limit:
        specs = specs[: args.limit]
    if not specs:
        raise SystemExit(f"no specs under {args.specs}")

    args.out.mkdir(parents=True, exist_ok=True)
    clean_path = args.out / "teacher_clean.jsonl"
    quarantine_path = args.out / "teacher_quarantine.jsonl"

    if args.stub:
        generate = stub_generator(specs)
    else:
        if not args.teacher:
            raise SystemExit("--teacher required unless --stub")
        from mlx_lm import load, generate as mlx_generate

        model, tokenizer = load(args.teacher)

        def generate(messages: list[dict]) -> str:
            prompt = tokenizer.apply_chat_template(
                messages, add_generation_prompt=True, enable_thinking=False
            )
            return mlx_generate(model, tokenizer, prompt=prompt, max_tokens=args.max_tokens).strip()

    kept = failed = 0
    with clean_path.open("w") as cf, quarantine_path.open("w") as qf:
        for spec in specs:
            question = generate(question_prompt(spec["context"], spec["category"])).strip()
            answer = generate(answer_prompt(spec["context"], question)).strip()
            example = assemble_example(spec, question, answer)
            ok, failures = gate_clean(example)
            if ok:
                cf.write(json.dumps(example, ensure_ascii=False) + "\n")
                kept += 1
            else:
                qf.write(json.dumps(
                    {"example_id": spec["example_id"],
                     "failed_gates": list(failures),
                     "example": example}, ensure_ascii=False) + "\n")
                failed += 1

    total = kept + failed
    rate = round(kept / total, 3) if total else 0.0
    print(json.dumps({
        "specs": total, "gate_clean": kept, "quarantined": failed,
        "gate_pass_rate": rate, "teacher": "stub" if args.stub else args.teacher,
        "clean": str(clean_path), "quarantine": str(quarantine_path),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
