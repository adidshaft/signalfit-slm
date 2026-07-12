#!/usr/bin/env python3
"""Generate the bounded 18-example iteration-17 grounded-quantity round.

One repair class only (iteration-16A data/capability defect): advice answers
that stay DIRECTIONAL ("a bit earlier", "a modest amount") or cite only
context numbers / exact same-unit derivations — never invented quantities
like the "30 minutes" bedtime shift ev1x-core2-000011 produced. Two plan
examples deliberately model the sanctioned derived-delta form (414 − 377 =
37 minutes) so the model learns what a grounded derivation looks like.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/synthetic/curated/agent_v9_micro"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


COHORT_CONSTRAINTS = {
    "sleep_coaching": {
        "must_mention": [
            "sleep duration steady: 405 minutes vs 406-minute weekly average",
            "recovery 56% below 65% weekly average",
            "small earlier bedtime shift, judged over several days",
        ],
        "must_not_mention": ["sleep stage values", "respiratory rate", "steps"],
        "required_behaviors": [
            "cites_user_baseline",
            "stays_directional_when_no_number_available",
            "offers_concrete_alternative",
        ],
        "forbidden_behaviors": [
            "invents_numbers",
            "population_stats_as_personal",
            "unsupported_habit_attribution",
        ],
    },
    "goal_coaching": {
        "must_mention": [
            "weekly average recovery 58% vs 67% target",
            "progress judged by weekly trend, not single days",
        ],
        "must_not_mention": ["strain value for today", "respiratory rate value", "steps"],
        "required_behaviors": [
            "cites_user_baseline",
            "declines_to_invent_timeline_or_rate",
            "encourages_without_overpromising",
        ],
        "forbidden_behaviors": [
            "invents_numbers",
            "population_stats_as_personal",
            "guarantees_outcome",
        ],
    },
    "plan_adjustment": {
        "must_mention": [
            "recovery 68% in line with weekly average",
            "sleep 377 minutes vs 414-minute weekly average",
            "no added volume until sleep recovers",
        ],
        "must_not_mention": ["activity strain value", "respiratory rate"],
        "required_behaviors": [
            "weighs_conflicting_signals",
            "gives_explicit_recommendation_level",
            "stays_directional_when_no_number_available",
        ],
        "forbidden_behaviors": [
            "invents_numbers",
            "population_stats_as_personal",
            "reflexive_rest_recommendation",
        ],
    },
}


def finish(example: dict, index: int, category: str, case_type: str, text: str, question: str) -> dict:
    example["example_id"] = f"agv9-micro-{index:03d}"
    example["context"]["request"]["user_question"] = question
    example["context"]["task"]["category"] = category
    example["task_category"] = category
    example["case_type"] = case_type
    example["target_response"]["text"] = text
    example["target_response"].update(COHORT_CONSTRAINTS[category])
    example["labels"]["persona_id"] = f"p-agv9-{index:03d}"
    example["labels"]["rubric_tags"] = ["sf-gates-12", "iteration17-micro", category, "grounded-quantity"]
    example["labels"]["is_locked_eval"] = False
    example["generation"] = {
        "generator": "agent-agent-workflow",
        "prompt_version": "agv9-micro-v1",
        "critic_passed": True,
        "human_reviewed": False,
        "created_at": "2026-07-12",
    }
    return example


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite {OUT}")
    OUT.mkdir(parents=True)
    # Template contexts (numbers referenced in golds are from these):
    # sleep: today 405 min, 7d avg 406 min, recovery 56% today / 65% 7d avg
    sleep = load("data/synthetic/curated/agent_v1/agen-v1-000281.json")
    # goal: recovery target 67%, today 55%, 7d avg 58%
    goal = load("data/synthetic/curated/agent_v1/agen-v1-000079.json")
    # plan: today sleep 377 min, 7d avg 414 min, recovery 68% today and 7d
    plan = load("data/synthetic/curated/agent_v1/agen-v1-000151.json")
    rows = []

    sleep_items = [
        ("i keep waking up tired even though my sleep looks the same. should i just go to bed earlier?",
         "Your sleep amount has been steady — 405 minutes last night against a 406-minute weekly average — but the weekly average recovery is 65% while this morning reads 56%, so the tiredness is more likely recovery than duration. Moving bedtime a bit earlier is still a reasonable experiment: keep the shift small, hold your usual wake time, and judge it over several mornings rather than one."),
        ("how much earlier should my bedtime be to stop feeling this flat in the mornings?",
         "There is no exact number in your data to prescribe, so keep it directional: shift bedtime slightly earlier and hold the change for a week. Your duration is already consistent — 405 minutes last night, 406 on the weekly average — so the flatness likely tracks recovery, which is 56% today against a 65% weekly average. A small, steady shift tells you more than a large one-off change."),
        ("would an extra hour in bed fix this tired feeling or is that overkill?",
         "Your data cannot confirm that a full extra hour is needed. Sleep is stable at 405 minutes last night and 406 minutes on the weekly average, while recovery is soft: a 65% weekly average with this morning at 56%. Start smaller: a modestly earlier bedtime with the same wake time, kept consistent for several nights. If mornings still feel flat after that, extend the window a little further."),
        ("my sleep duration barely changes night to night, so why do i feel worse this week?",
         "Consistency is real in your numbers: 405 minutes last night, 406 minutes on the weekly average. What changed is recovery — 56% today against a weekly average of 65% — and your resting heart rate is running above its usual level. Duration alone does not capture sleep quality or accumulated load. Keep the schedule, nudge bedtime slightly earlier, and let a few mornings of trend data show whether the dip is passing."),
        ("should i change my whole evening routine or just sleep a bit longer?",
         "Change one thing at a time, and keep it small. Your duration is steady — 405 minutes last night against a 406-minute weekly average — so a wholesale routine rebuild is not supported by the data. The softer signal is recovery at 56% today versus a 65% weekly average. A slightly earlier bedtime, unchanged wake time, and a calm final hour is enough of an experiment; judge it over the week, not overnight."),
        ("is my tiredness a sleep problem or a training problem, and what do i adjust first?",
         "Your sleep quantity looks stable — 405 minutes last night, 406 minutes on the weekly average — while recovery is 56% today against a 65% weekly average, so the load side deserves the first look. Adjust in small, reversible steps: keep training but trim intensity slightly, and move bedtime a little earlier. If recovery drifts back toward its usual range over the week, you have your answer without a bigger change."),
        ("do i need a strict new sleep schedule with exact times to fix this?",
         "Exact times are not something your data can justify — what it shows is steady duration, 405 minutes last night against a 406-minute weekly average, with recovery at 56% today versus 65% for the week. The useful move is directional: a somewhat earlier bedtime, the same wake time every day, and a consistent wind-down. Precision matters less than repetition here; hold the pattern for a week and reassess against your own trend."),
    ]

    goal_items = [
        ("im stuck in the 50s chasing my 67 recovery target. is it even moving?",
         "A snapshot cannot settle whether it is moving: your weekly average is 58%, with this morning at 55%, against the 67% target, and one morning scatters too much to carry a verdict. What supports progress is the boring stuff — steady sleep, easy days that stay easy, and consistent measurement conditions. Watch the weekly average over the coming weeks rather than single days; its direction is what tells you whether the plan is working."),
        ("how many weeks until i hit my recovery target if i keep doing what im doing?",
         "Your data cannot produce a reliable week count, and inventing one would mislead you. What it does show: a weekly average recovery of 58%, this morning at 55%, and the target at 67%. The weekly average is the honest progress marker — if it climbs over the next few weeks, you are on track; if it stalls, the first levers are sleep consistency and keeping easy sessions genuinely easy. Judge by trend direction, not a countdown."),
        ("should i set a smaller intermediate recovery goal instead of 67?",
         "That can help, provided it stays anchored to your data. Your weekly average recovery is 58% and today reads 55%, so an intermediate marker a step past your current weekly average is natural on the way to the 67% target. The value is psychological and practical: you evaluate progress against a nearby reference instead of a distant one. Keep measuring under similar conditions so the comparison stays meaningful week to week."),
        ("whats a realistic daily improvement rate for recovery scores?",
         "Recovery does not improve at a fixed daily rate, and your data does not contain one to quote. The reliable frame is your weekly average — currently 58%, with today at 55% and the target at 67%. Progress shows up as that weekly number drifting upward over several weeks, not as daily increments. Protect sleep, keep hard days genuinely hard and easy days easy, and reassess the trend weekly rather than scoring each morning."),
        ("give me an exact plan with numbers to get from 55 to 67 recovery.",
         "An honest plan works in directions, not invented numbers: your data shows today at 55%, a weekly average of 58%, and the 67% target, but no formula for daily gains. Concretely — keep a consistent sleep window, hold most sessions easy with hard work concentrated on your strongest days, and review the weekly average each week. If it trends upward for a few weeks, hold course; if it stalls, ease total load slightly before changing anything else."),
    ]

    plan_items = [
        ("readiness is high but i slept badly. is adding an extra swim this week smart?",
         "Hold off for now. Your recovery score is 68% today, in line with your weekly average of 68%, but last night's sleep was 377 minutes against a 414-minute weekly average — a 37-minute shortfall by exact comparison. Adding volume on a short night front-loads risk for little gain. Keep the planned sessions, see whether tonight's sleep returns toward your average, and add the swim later in the week if it does."),
        ("can i squeeze in one more hard session this week or should i wait?",
         "Wait one more day before deciding. Recovery reads 68% today, matching your weekly average of 68%, which supports training as planned — but last night's 377 minutes sits well under your 414-minute weekly average, and stacking a new hard session on a short night is where plans usually crack. Run today as scheduled, protect tonight's sleep, and add the extra session only once your sleep is back near its usual level."),
        ("my readiness score says go but my body says meh. which do i trust for adding volume?",
         "Trust the fuller picture. The readiness side is genuine — recovery is 68% today, right at your weekly average of 68% — but sleep tells the other half: 377 minutes last night against a 414-minute weekly average. When the two disagree, the conservative read wins for volume additions. Keep today's planned work, skip the add-on for now, and revisit once your sleep returns to its usual range for a night or two."),
        ("if i add the swim, should i also shorten my other sessions to compensate?",
         "Better to hold the swim for now than to juggle compensations. Your recovery is steady at 68% today against a 68% weekly average, but last night's sleep was 377 minutes against your 414-minute weekly average — a 37-minute gap by exact comparison. Once sleep is back near its usual level, add the swim with an explicit trade: trim intensity or duration modestly from one existing session rather than shaving all of them, and keep your hardest day untouched."),
        ("how much extra training can my current recovery actually support?",
         "There is no exact capacity number in your data, so resist inventing one. What it shows: recovery at 68% today, level with your weekly average of 68%, and sleep at 377 minutes last night against a 414-minute weekly average. Steady recovery supports your current plan; the short night argues against adding more right now. If sleep returns to its usual level for a few nights, add one modest session and watch how the weekly numbers respond."),
        ("is one bad night of sleep enough reason to change this week's plan?",
         "Usually not — one short night justifies caution about additions, not a rewrite. Your recovery is holding at 68% today, matching the weekly average of 68%, so the base plan stands. Last night's 377 minutes against your 414-minute weekly average is worth respecting at the margins: keep the scheduled sessions, drop the idea of extra volume for a day or two, and let the weekly averages, not a single night, drive any structural change."),
    ]

    index = 0
    for template, category, case_type, items in (
        (sleep, "sleep_coaching", "edge", sleep_items),
        (goal, "goal_coaching", "edge", goal_items),
        (plan, "plan_adjustment", "edge", plan_items),
    ):
        for question, text in items:
            rows.append(finish(copy.deepcopy(template), index, category, case_type, text, question))
            index += 1

    for row in rows:
        (OUT / f"{row['example_id']}.json").write_text(
            json.dumps(row, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        )
    print(f"wrote {len(rows)} examples to {OUT}")


if __name__ == "__main__":
    main()
