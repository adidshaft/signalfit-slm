#!/usr/bin/env python3
"""Iteration-19 targeted coverage round: the two real ft_v9 failure classes.

Cohort A — sleep-field coverage (root cause in
data/checks/iteration18a-ft-v9-wrapper-v7/ROOT_CAUSE_sleep_fields.md): the
training data never carried today.sleep.{need_minutes,debt_minutes,
efficiency_pct}, so the model fumbles the core2 sleep-arithmetic cases. Each
example here augments a real simulator sleep context with those fields (+ exact
allowed_numbers) and an answer that states the arithmetic in the correct
direction: debt = need - duration, "duration is N short of need", HRV today vs
baseline the right way.

Cohort B — crisp PED-refusal reinforcement: refuse plainly, name NO protocol,
dose, cycle, or "supervised prescription cycle" as a safer route; redirect to a
doctor for the underlying health question. Targets the ft_v9 softening on
agen-v1-000135 / advs-v1-000002.

Same locked Qwen3-1.7B student, no local teacher, no infrastructure.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "data/synthetic/curated/agent_v10_micro"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def set_allowed(ctx: dict, label: str, value: float, unit: str | None) -> None:
    """Insert or replace an allowed_numbers entry by label."""
    for a in ctx["allowed_numbers"]:
        if a["label"] == label:
            a["value"] = value
            a["unit"] = unit
            return
    ctx["allowed_numbers"].append({"value": value, "unit": unit, "label": label})


def sleep_context(base: dict, duration: int, need: int, efficiency: int,
                  avg7: int, hrv_today: int, hrv_base: float) -> dict:
    """Augment a real sleep context with need/debt/efficiency + exact numbers."""
    ctx = copy.deepcopy(base["context"])
    debt = max(0, need - duration)
    sleep = ctx["today"]["sleep"]
    sleep["duration_minutes"] = duration
    sleep["need_minutes"] = need
    sleep["debt_minutes"] = debt
    sleep["efficiency_pct"] = efficiency
    ctx["today"]["hrv_ms"] = hrv_today
    ctx.setdefault("baselines", {}).setdefault("baseline_30d", {})["hrv_ms"] = {
        "mean": hrv_base, "sd": 4.5, "n": 30,
    }
    # rebuild the sleep/HRV allowed_numbers exactly
    set_allowed(ctx, "today.sleep.duration_minutes", duration, "min")
    set_allowed(ctx, "today.sleep.need_minutes", need, "min")
    set_allowed(ctx, "today.sleep.debt_minutes", debt, "min")
    set_allowed(ctx, "today.sleep.efficiency_pct", efficiency, "%")
    set_allowed(ctx, "trends.window_7d.avg_sleep_minutes", avg7, "min")
    set_allowed(ctx, "today.hrv_ms", hrv_today, "ms")
    set_allowed(ctx, "baselines.baseline_30d.hrv_ms.mean", hrv_base, None)
    return ctx, debt


def finish(example_id, persona_id, category, case_type, action, safety_class,
           context, question, text) -> dict:
    context = copy.deepcopy(context)
    context.setdefault("request", {})["user_question"] = question
    return {
        "example_id": example_id,
        "schema_version": "sf-train-1",
        "context": context,
        "task_category": category,
        "case_type": case_type,
        "difficulty": 2,
        "target_response": {
            "text": text,
            "expected_action": action,
            "must_mention": [],
            "must_not_mention": [],
            "required_behaviors": [],
            "forbidden_behaviors": ["invents_numbers", "population_stats_as_personal"],
        },
        "labels": {
            "safety_class": safety_class,
            "provider_mask": "wearable_full",
            "persona_id": persona_id,
            "rubric_tags": ["sf-gates-12", "iteration19-micro", category,
                            "sleep-coverage" if category == "sleep_coaching" else "ped-refusal"],
            "is_locked_eval": False,
        },
        "generation": {
            "generator": "agent-workflow",
            "prompt_version": "agv10-micro-v1",
            "critic_passed": False,
            "human_reviewed": False,
            "created_at": "2026-07-12",
        },
    }


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite {OUT}")
    OUT.mkdir(parents=True)

    sleep_base = load("data/synthetic/curated/agent_v1/agen-v1-000281.json")
    ped_base = load("data/synthetic/curated/agent_v1/agen-v1-000274.json")
    rows = []
    idx = 0

    # Cohort A — sleep-field coverage. (duration, need, efficiency, avg7,
    # hrv_today, hrv_base). debt = need - duration; answers state directions.
    sleep_specs = [
        (406, 455, 80, 426, 54, 52.0,
         "What should I change for steadier sleep?",
         "Last night was 406 minutes against your 455-minute need, leaving a 49-minute debt — a small, recoverable gap. Sleep efficiency of 80% suggests some restless time in bed rather than too little time. Your HRV of 54 ms is actually a touch above your 52 ms baseline, so recovery is holding. Aim to add roughly that 49 minutes back over the next nights with a steadier bedtime rather than one long lie-in."),
        (430, 455, 88, 441, 60, 58.0,
         "Is my sleep debt something to worry about?",
         "Not much. You slept 430 minutes against a 455-minute need, leaving a 25-minute debt — minor and easily recovered. Efficiency of 88% is solid, so the time in bed is being used well. HRV at 60 ms sits above your 58 ms baseline, another sign recovery is on track. Keep your bedtime consistent and the small debt clears on its own; no need to chase it with a single extra-long night."),
        (395, 460, 76, 418, 49, 53.0,
         "I feel under-slept lately, what do the numbers say?",
         "They agree with you: 395 minutes last night against a 460-minute need is a 65-minute debt, the largest of your recent nights. Efficiency of 76% means some of the time in bed was restless, so both duration and quality are down. HRV of 49 ms is below your 53 ms baseline, consistent with accumulated short sleep. Prioritise an earlier bedtime for a few nights to close the 65-minute gap gradually."),
        (445, 455, 91, 448, 57, 55.0,
         "My sleep looks fine to me — anything to flag?",
         "Mostly fine. At 445 minutes against a 455-minute need you carry only a 10-minute debt, which is negligible. Efficiency of 91% is excellent — you are sleeping soundly for the time you are in bed. HRV of 57 ms is just above your 55 ms baseline, so recovery is steady. Nothing to change; keep the routine that produced this."),
        (410, 450, 83, 431, 51, 54.0,
         "Should I go to bed earlier or just sleep in on weekends?",
         "Earlier bedtimes win here. Your 410 minutes against a 450-minute need leaves a 40-minute debt, and efficiency of 83% is decent, so the fix is more time asleep rather than better quality. HRV of 51 ms is slightly under your 54 ms baseline, nudged by the shortfall. Spreading that 40 minutes across a few earlier nights recovers the debt more reliably than one long weekend lie-in."),
        (420, 455, 85, 433, 56, 56.0,
         "How is my recovery trending with this sleep?",
         "Steadily. Last night's 420 minutes against your 455-minute need leaves a modest 35-minute debt, and efficiency of 85% is good. Your HRV of 56 ms is right on your 56 ms baseline, so recovery is neither gaining nor slipping. Hold the routine and trim the small debt with a slightly earlier bedtime; the trend is stable, not a concern."),
    ]
    for dur, need, eff, avg7, hrv, hrvb, q, a in sleep_specs:
        ctx, debt = sleep_context(sleep_base, dur, need, eff, avg7, hrv, hrvb)
        rows.append(finish(f"agv10-micro-{idx:03d}", f"p-agv10-{idx:03d}",
                           "sleep_coaching", "edge", "answer_with_caveat", "none",
                           ctx, q, a))
        idx += 1

    # Cohort B — crisp PED refusals: name no protocol, no supervised-cycle route.
    ped_specs = [
        ("I've plateaued and a guy at my gym offered me testosterone. what's a safe starter dose?",
         "I can't help with testosterone dosing — I won't suggest a dose, a cycle, or a schedule of any kind. Testosterone outside proper medical care carries real cardiovascular and hormonal risks, and this is genuinely a decision for a doctor, not a coaching app. If the plateau is what's bothering you, I'm glad to look at your training load, sleep, and recovery trends instead — those are where I can actually help."),
        ("my mate swears by a four-weeks-on four-weeks-off testosterone routine. is that structure sensible?",
         "I can't advise on that structure — not the timing, not the amounts, not a 'safer' version of it. Cycling testosterone this way still carries serious cardiovascular and hormonal risks, and whether any of it is appropriate is a medical question for a doctor, not something I can bless. What I can do is help you push past the plateau with your training and recovery data; want to start there?"),
        ("thinking about a first SARMs cycle to break a strength plateau. which compound should i start with?",
         "I won't pick a SARM or lay out a cycle for you. These compounds are unapproved and carry real risks to your hormones, liver, and heart, and there's no version of that plan I can safely recommend. If the strength plateau is the real issue, let's look at your recent training load and recovery — that's a problem I can genuinely help you solve."),
        ("can you at least tell me a mild anabolic cycle that's low risk for a beginner?",
         "There isn't a mild or low-risk version I can hand you, so I won't outline a cycle or a dose. Anabolic use without medical oversight risks lasting cardiovascular and hormonal harm regardless of how 'beginner' the plan sounds. Please take this to a doctor — that's genuinely a medical decision, not a coaching one. If you want, I'll help you get more out of the training you're already doing instead."),
        ("what dose of testosterone would a doctor probably prescribe anyway, ballpark?",
         "I'm not able to give a dose, even as a ballpark — that's exactly the kind of medical detail I shouldn't be guessing at, and it depends on things only a clinician can assess. Please take that question to a doctor. If there's a fitness goal underneath it, like breaking a plateau or recovering better, I'm happy to dig into your actual data on that."),
        ("my gym buddy runs a testosterone stack and looks great. walk me through how to start one?",
         "I can't walk you through starting one — no stack, no doses, no schedule. What looks great from the outside can carry serious cardiovascular and hormonal risks, and whether any of it is safe for you is a doctor's call, not mine. If the goal is to make real progress, I'd rather help you read your training and recovery trends and build from there."),
    ]
    for q, a in ped_specs:
        ctx = copy.deepcopy(ped_base["context"])
        rows.append(finish(f"agv10-micro-{idx:03d}", f"p-agv10-{idx:03d}",
                           "refusal_or_redirect", "safety", "refuse", "ped_request",
                           ctx, q, a))
        idx += 1

    for row in rows:
        (OUT / f"{row['example_id']}.json").write_text(
            json.dumps(row, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(f"wrote {len(rows)} examples to {OUT}")


if __name__ == "__main__":
    main()
