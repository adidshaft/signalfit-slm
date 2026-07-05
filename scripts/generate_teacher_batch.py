#!/usr/bin/env python3
"""Generate training examples with a frontier teacher model via the Batch API.

DO NOT RUN without an Anthropic API key and explicit user approval — it costs
real money (estimate printed at submit time; Batch API bills at 50% of standard
prices).

Architecture: contexts are built DETERMINISTICALLY by the same simulator as the
seed dataset (numbers coherent by construction, allowed_numbers auto-collected);
the teacher model writes only the natural language — question, answer, behavior
labels — under the rules of prompts/synthetic_data_generation.md. Structured
outputs guarantee parseable JSON; the grounding gate re-checks every answer on
collect, and rejects are quarantined for regeneration.

Usage:
    # 1. Submit a batch (writes specs + batch id to the out dir)
    .venv/bin/python scripts/generate_teacher_batch.py submit \
        --count 100 --seed 101 --out data/synthetic/raw/batch_v1

    # 2. Later: collect results, assemble + gate examples
    .venv/bin/python scripts/generate_teacher_batch.py collect \
        --out data/synthetic/raw/batch_v1
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_seed_dataset import CATEGORIES, SAFETY_FLAGS, build_context, make_series  # noqa: E402
from validate_schema import NUM_UNIT  # noqa: E402

TEACHER_MODEL = "agent-opus-4-8"  # $5/$25 per MTok, 50% off via Batch API
PROMPT_VERSION = "gen-1-batch-1"

# data_generation_plan.md §2 distribution (weights) and §3 case mix
CATEGORY_WEIGHTS = {
    "daily_training_decision": 18, "explain_metric": 14, "recovery_explanation": 12,
    "sleep_coaching": 12, "insufficient_data_followup": 10, "safety_triage": 9,
    "plan_adjustment": 8, "goal_coaching": 7, "habit_pattern_analysis": 6,
    "refusal_or_redirect": 4,
}
MASKS = ["wearable_full", "wearable_full", "wearable_full", "ring_no_strain",
         "platform_aggregate", "manual_only"]

TEACHER_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "answer": {"type": "string"},
        "expected_action": {"enum": ["answer", "answer_with_caveat", "followup", "triage", "refuse"]},
        "must_mention": {"type": "array", "items": {"type": "string"}},
        "must_not_mention": {"type": "array", "items": {"type": "string"}},
        "required_behaviors": {"type": "array", "items": {"type": "string"}},
        "forbidden_behaviors": {"type": "array", "items": {"type": "string"}},
        "difficulty": {"enum": [1, 2, 3]},
    },
    "required": ["question", "answer", "expected_action", "must_mention", "must_not_mention",
                 "required_behaviors", "forbidden_behaviors", "difficulty"],
    "additionalProperties": False,
}


def system_prompt() -> str:
    repo = Path(__file__).resolve().parent.parent
    gen_rules = (repo / "prompts" / "synthetic_data_generation.md").read_text()
    safety = (repo / "docs" / "safety_policy.md").read_text()
    return (
        "You write one training example for SignalFit-SLM, a small on-device fitness "
        "assistant grounded ONLY in a context JSON. You are given the CONTEXT (already "
        "built, do not alter it), a TASK CATEGORY, a CASE TYPE, and safety flags. "
        "Write the user QUESTION (natural, casual, varied voice; embed safety triggers "
        "naturally when flags are present) and the ideal ANSWER, plus behavior labels.\n\n"
        "Non-negotiable rules:\n"
        "- Every number+unit you write in the answer must exist in the context's "
        "allowed_numbers (tolerance +/-1.0). Cite the user's values vs their own baseline.\n"
        "- Follow the answer-shape, hedging, and hard-ban rules below.\n"
        "- Follow the safety policy below exactly for safety/lookalike cases.\n\n"
        f"=== GENERATION RULES ===\n{gen_rules}\n\n=== SAFETY POLICY ===\n{safety}"
    )


def build_specs(count: int, seed: int):
    rng = random.Random(seed)
    categories = rng.choices(list(CATEGORY_WEIGHTS), weights=CATEGORY_WEIGHTS.values(), k=count)
    specs = []
    for i, category in enumerate(categories):
        case_roll = rng.random()
        if category in ("safety_triage", "refusal_or_redirect"):
            case_type = "safety"
        elif case_roll < 0.10:
            case_type = "safety_lookalike"
        elif case_roll < 0.35:
            case_type = "edge"
        else:
            case_type = "normal"
        variant = rng.randrange(3)
        persona = {
            "series": make_series(rng, fit=rng.uniform(0.15, 0.95)),
            "age_band": rng.choice(["18-24", "25-29", "30-34", "40-44", "50-54", "60-64"]),
            "sex": rng.choice(["male", "female"]),
            "workout_type": rng.choice(["run", "strength", "cycle", "swim", "row", "hike"]),
            "workout_min": rng.randint(25, 90),
            "workout_avg_hr": rng.randint(115, 160),
            "workout_peak_hr": rng.randint(158, 192),
            "category": category,
            "safety_flags": SAFETY_FLAGS.get(category, [[], [], [], [], []])[variant % 5],
        }
        mask = "manual_only" if category == "insufficient_data_followup" else rng.choice(MASKS)
        ctx = build_context(persona, "", mask)
        specs.append({
            "example_id": f"teach-v1-{seed}-{i:06d}",
            "category": category, "case_type": case_type, "mask": mask,
            "persona_id": f"p-teach-{seed}-{i:04d}",
            "context": ctx,
        })
    return specs


def user_message(spec: dict) -> str:
    ctx_json = json.dumps(spec["context"], separators=(",", ":"), sort_keys=True)
    return (f"TASK CATEGORY: {spec['category']}\nCASE TYPE: {spec['case_type']}\n"
            f"SAFETY FLAGS: {spec['context']['safety_flags']}\n\nCONTEXT:\n{ctx_json}")


def cmd_submit(args) -> int:
    import anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    specs = build_specs(args.count, args.seed)
    (out / "specs.json").write_text(json.dumps(specs, indent=1))

    system = [{"type": "text", "text": system_prompt(),
               "cache_control": {"type": "ephemeral"}}]
    requests = [
        Request(
            custom_id=spec["example_id"],
            params=MessageCreateParamsNonStreaming(
                model=TEACHER_MODEL,
                max_tokens=1200,
                system=system,
                output_config={"format": {"type": "json_schema", "schema": TEACHER_SCHEMA}},
                messages=[{"role": "user", "content": user_message(spec)}],
            ),
        )
        for spec in specs
    ]

    # rough cost estimate before committing (batch = 50% of $5/$25 per MTok)
    in_tokens = args.count * 2600  # system (mostly cached) + context + instructions
    out_tokens = args.count * 500
    print(f"~cost estimate: ${in_tokens/1e6*2.5 + out_tokens/1e6*12.5:.2f} "
          f"({args.count} examples, batch pricing, ignoring cache savings)")
    if not args.yes:
        raise SystemExit("dry run — re-run with --yes to submit")

    client = anthropic.Anthropic()
    batch = client.messages.batches.create(requests=requests)
    (out / "batch.json").write_text(json.dumps({"batch_id": batch.id, "model": TEACHER_MODEL,
                                                "prompt_version": PROMPT_VERSION,
                                                "count": args.count, "seed": args.seed}, indent=2))
    print(f"submitted batch {batch.id} ({args.count} requests) -> {out}/batch.json")
    return 0


def cmd_collect(args) -> int:
    import anthropic

    out = Path(args.out)
    meta = json.loads((out / "batch.json").read_text())
    specs = {s["example_id"]: s for s in json.loads((out / "specs.json").read_text())}
    client = anthropic.Anthropic()

    batch = client.messages.batches.retrieve(meta["batch_id"])
    if batch.processing_status != "ended":
        print(f"batch {meta['batch_id']} still {batch.processing_status} "
              f"({batch.request_counts.processing} processing) — retry later")
        return 1

    accepted_dir = out / "accepted"
    rejected_dir = out / "rejected"
    accepted_dir.mkdir(exist_ok=True)
    rejected_dir.mkdir(exist_ok=True)
    n_ok = n_bad = 0
    for result in client.messages.batches.results(meta["batch_id"]):
        spec = specs[result.custom_id]
        if result.result.type != "succeeded":
            (rejected_dir / f"{result.custom_id}.error.json").write_text(
                json.dumps({"error": result.result.type}))
            n_bad += 1
            continue
        msg = result.result.message
        text = next((b.text for b in msg.content if b.type == "text"), "")
        teacher = json.loads(text)  # structured outputs guarantee schema-valid JSON

        ctx = spec["context"]
        ctx["request"]["user_question"] = teacher["question"]
        example = {
            "example_id": spec["example_id"],
            "schema_version": "sf-train-1",
            "context": ctx,
            "task_category": spec["category"],
            "case_type": spec["case_type"],
            "difficulty": teacher["difficulty"],
            "target_response": {
                "text": teacher["answer"],
                "expected_action": teacher["expected_action"],
                "must_mention": teacher["must_mention"],
                "must_not_mention": teacher["must_not_mention"],
                "required_behaviors": teacher["required_behaviors"],
                "forbidden_behaviors": teacher["forbidden_behaviors"],
            },
            "labels": {
                "safety_class": "medical_red_flag" if spec["category"] == "safety_triage"
                else ("ped_request" if spec["category"] == "refusal_or_redirect" else "none"),
                "provider_mask": spec["mask"],
                "persona_id": spec["persona_id"],
                "rubric_tags": ["grounding", "behavior_compliance"],
                "is_locked_eval": False,
            },
            "generation": {"generator": meta["model"], "prompt_version": meta["prompt_version"],
                           "critic_passed": None, "human_reviewed": False},
        }
        allowed = [a["value"] for a in ctx["allowed_numbers"]]
        ungrounded = [m.group(0) for m in NUM_UNIT.finditer(teacher["answer"])
                      if not any(abs(v - float(m.group(1))) <= 1.0 for v in allowed)]
        target = rejected_dir if ungrounded else accepted_dir
        if ungrounded:
            example["_rejection"] = {"ungrounded": ungrounded}
            n_bad += 1
        else:
            n_ok += 1
        (target / f"{spec['example_id']}.json").write_text(
            json.dumps(example, indent=2, ensure_ascii=False) + "\n")

    print(f"accepted {n_ok}, rejected {n_bad} -> {out}\n"
          f"next: validate_schema.py {accepted_dir}, then prepare/split")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("submit")
    s.add_argument("--count", type=int, default=100)
    s.add_argument("--seed", type=int, default=101)
    s.add_argument("--out", required=True)
    s.add_argument("--yes", action="store_true", help="actually submit (else dry run)")
    s.set_defaults(func=cmd_submit)
    c = sub.add_parser("collect")
    c.add_argument("--out", required=True)
    c.set_defaults(func=cmd_collect)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
