#!/usr/bin/env python3
"""Build deterministic context specs for agent-workflow generation (no APIs).

Usage:
    .venv/bin/python scripts/make_context_specs.py --seed 301 \
        --out data/synthetic/raw/agent_v1/specs --chunk-size 30

Produces chunk_NN.json files, each a list of specs: {example_id, category,
case_type, mask, persona_id, is_locked_eval, context}. Contexts come from the
same simulator as the seed set (coherent numbers, allowed_numbers complete).
The generator agent writes only question/answer/labels.

Phase-1 category plan (user-specified, 2026-07-05) totals 300; ~10% per
category are locked-eval specs on a disjoint eval-persona namespace.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_seed_dataset import SAFETY_FLAGS, build_context, make_series  # noqa: E402

PLAN = {
    "explain_metric": 40, "daily_training_decision": 45, "recovery_explanation": 40,
    "sleep_coaching": 35, "plan_adjustment": 35, "goal_coaching": 30,
    "habit_pattern_analysis": 25, "insufficient_data_followup": 20,
    "safety_triage": 20, "refusal_or_redirect": 10,
}
MASKS = ["wearable_full", "wearable_full", "wearable_full", "ring_no_strain",
         "platform_aggregate", "manual_only"]


def case_type_for(category: str, rng: random.Random) -> str:
    if category in ("safety_triage", "refusal_or_redirect"):
        return "safety"
    roll = rng.random()
    if category == "daily_training_decision" and roll < 0.12:
        return "safety_lookalike"
    if roll < 0.35:
        return "edge"
    return "normal"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=301)
    ap.add_argument("--out", required=True)
    ap.add_argument("--chunk-size", type=int, default=30)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    specs = []
    for category, count in PLAN.items():
        n_locked = max(1, round(count * 0.1))
        for j in range(count):
            locked = j >= count - n_locked
            variant = rng.randrange(5)
            persona = {
                "series": make_series(rng, fit=rng.uniform(0.15, 0.95)),
                "age_band": rng.choice(["18-24", "25-29", "30-34", "40-44", "50-54", "60-64"]),
                "sex": rng.choice(["male", "female"]),
                "workout_type": rng.choice(["run", "strength", "cycle", "swim", "row", "hike"]),
                "workout_min": rng.randint(25, 90),
                "workout_avg_hr": rng.randint(115, 160),
                "workout_peak_hr": rng.randint(158, 192),
                "category": category,
                "safety_flags": SAFETY_FLAGS.get(category, [[], [], [], [], []])[variant],
            }
            mask = ("manual_only" if category == "insufficient_data_followup"
                    else rng.choice(MASKS))
            specs.append({
                "category": category,
                "case_type": case_type_for(category, rng),
                "mask": mask,
                "persona_id": (f"eval-p-agen-{category[:10]}-{j}" if locked
                               else f"p-agen-{args.seed}-{category[:10]}-{j}"),
                "is_locked_eval": locked,
                "context": build_context(persona, "", mask),
            })

    rng.shuffle(specs)
    for i, spec in enumerate(specs):
        spec["example_id"] = f"agen-v1-{i:06d}"

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for n, start in enumerate(range(0, len(specs), args.chunk_size), 1):
        chunk = specs[start:start + args.chunk_size]
        (out / f"chunk_{n:02d}.json").write_text(json.dumps(chunk, indent=1) + "\n")
    print(f"{len(specs)} specs -> {out} in {n} chunks of <= {args.chunk_size} "
          f"(locked eval: {sum(s['is_locked_eval'] for s in specs)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
