#!/usr/bin/env python3
"""Create the isolated agv7 daily-decision repair slice (training only)."""
from __future__ import annotations

import json
from pathlib import Path


OUT = Path(__file__).parent


NORMAL = [
    ("easy", "Your HRV is below its usual level, resting heart rate is higher than baseline, and last night's sleep was shorter than normal.", "take a relaxed walk outdoors", "trail run"),
    ("easy", "HRV is suppressed relative to baseline, resting heart rate is elevated, and sleep did not match your routine.", "do a gentle mobility session", "track intervals"),
    ("moderate", "HRV is near its usual level, resting heart rate is steady, and sleep was adequate even after yesterday's load.", "complete the planned strength session with lighter loads", "barbell session"),
    ("as-planned", "HRV is close to baseline, resting heart rate is steady, and sleep was consistent with your recent routine.", "complete the planned ride at the intended effort", "road ride"),
    ("harder-ok", "HRV is above its usual level, resting heart rate is lower than baseline, and sleep was solid.", "add the planned final interval", "pool workout"),
    ("easy", "The seven-day trend shows accumulating load, HRV is below baseline, and sleep was short.", "swap the tempo session for easy cycling", "tempo run"),
    ("moderate", "Your current HRV is typical, resting heart rate is typical, and sleep was steady despite mild soreness.", "do the planned upper-body workout", "upper-body workout"),
    ("as-planned", "HRV is stable, resting heart rate is near baseline, and sleep has been consistent across recent nights.", "follow the planned swim set", "swim set"),
    ("easy", "HRV has dipped for several days, resting heart rate is higher than normal, and sleep debt is showing in the trend.", "choose an easy spin", "hill repeats"),
    ("harder-ok", "HRV is strong relative to baseline, resting heart rate is steady, and last night's sleep was restorative.", "keep the planned progression run", "progression run"),
    ("moderate", "HRV is near baseline, resting heart rate is steady, and sleep was adequate but not exceptional.", "make the planned session a controlled circuit", "circuit session"),
    ("as-planned", "HRV is stable, resting heart rate is normal for you, and sleep duration matched your recent pattern.", "do the planned rowing workout", "rowing workout"),
    ("easy", "HRV is lower than your baseline, resting heart rate rose after a hard weekend, and sleep was shortened.", "take an easy walk", "long run"),
    ("moderate", "HRV is typical, resting heart rate is steady, and sleep was sufficient after a low-load day.", "complete the planned technique session", "climbing session"),
    ("as-planned", "HRV sits near its personal baseline, resting heart rate is unchanged, and sleep quality was consistent.", "complete the planned kettlebell workout", "kettlebell workout"),
    ("harder-ok", "HRV is higher than usual, resting heart rate is below baseline, and sleep was consistent over recent nights.", "include the planned hill segment", "hike"),
    ("easy", "HRV is below your usual reading, resting heart rate is elevated, and sleep was interrupted.", "choose a calm yoga class", "boxing drills"),
    ("moderate", "HRV is steady, resting heart rate is close to baseline, and sleep was adequate following a rest day.", "do the planned pilates session", "pilates session"),
    ("as-planned", "HRV is typical for you, resting heart rate is steady, and sleep matched the prior week's pattern.", "complete the planned dance class", "dance class"),
    ("easy", "HRV is lower than normal, resting heart rate is elevated, and sleep was shorter after travel.", "take a gentle neighborhood walk", "gym session"),
    ("moderate", "HRV is close to baseline, resting heart rate is steady, and sleep was consistent even with a busy workday.", "do the planned easy run", "easy run"),
    ("as-planned", "HRV remains stable, resting heart rate is normal for you, and sleep was in line with your routine.", "complete the planned ski-erg workout", "ski-erg workout"),
    ("harder-ok", "HRV is above baseline, resting heart rate is lower than usual, and sleep was long and consistent.", "keep the planned threshold block", "threshold block"),
    ("easy", "HRV is suppressed, resting heart rate is higher than baseline, and sleep was brief after a late shift.", "do an easy stretching routine", "interval ride"),
]

MISSING = [
    ("easy", "HRV is below baseline, resting heart rate is higher, and sleep was shorter than usual.", "take a relaxed walk", "fartlek run"),
    ("moderate", "HRV is near its usual level, resting heart rate is steady, and sleep was adequate.", "complete the planned strength session with lighter loads", "strength session"),
    ("as-planned", "HRV is stable, resting heart rate is near baseline, and sleep matched your routine.", "complete the planned ride", "gravel ride"),
    ("easy", "HRV is suppressed, resting heart rate is elevated, and sleep was interrupted.", "choose gentle mobility work", "speed workout"),
    ("harder-ok", "HRV is above baseline, resting heart rate is lower, and sleep was consistent.", "add the planned final repeat", "track workout"),
    ("moderate", "HRV is typical, resting heart rate is steady, and sleep was adequate.", "do the planned technique practice", "martial-arts class"),
    ("easy", "HRV has fallen, resting heart rate has risen, and sleep was short.", "take an easy spin", "stair workout"),
    ("as-planned", "HRV is steady, resting heart rate is normal for you, and sleep was consistent.", "complete the planned swim", "swim workout"),
    ("easy", "HRV is lower than baseline, resting heart rate is higher, and sleep was shorter after travel.", "take a calm walk", "lifting session"),
    ("moderate", "HRV is near baseline, resting heart rate is steady, and sleep was sufficient.", "do the planned yoga flow", "yoga flow"),
    ("as-planned", "HRV is typical, resting heart rate is stable, and sleep aligned with your routine.", "complete the planned row", "rowing session"),
    ("harder-ok", "HRV is above usual, resting heart rate is lower, and sleep was strong.", "keep the planned hill finish", "trail hike"),
]

SAFETY = [
    ("user_mentions_chest_pain", "I felt pressure in my chest after breakfast. Can I still do my planned run?", "New chest pressure is a red-flag symptom, and wearable values cannot determine whether exercise is safe.", "Seek immediate medical care now."),
    ("user_mentions_fainting", "I blacked out briefly while standing in the kitchen. Should I lift this evening?", "A fainting episode is a red flag, and the available training data cannot clear you for exercise.", "Seek immediate medical care now."),
    ("user_mentions_breathing_difficulty", "I am short of breath while resting today; can I make up yesterday's workout?", "Breathing difficulty at rest is a red flag, and readiness data cannot establish that activity is safe.", "Seek immediate medical care now."),
    ("injury_mention", "My ankle pain is sharp and I am limping. Should I push through my class?", "Sharp pain that changes how you walk needs assessment, and a wearable cannot determine the injury's severity.", "Arrange prompt clinical or physiotherapy evaluation."),
    ("other_red_flag", "My urine looked dark after a brutal workout and I feel weak. Is an easy run okay?", "Dark urine after hard exercise with weakness is a red flag, and the available signals cannot rule out a serious problem.", "Seek immediate medical care now."),
    ("possible_illness_pattern", "I have feverish chills and my readings are off. Can I train to sweat it out?", "Feverish symptoms are a safety concern, and the wearable pattern cannot diagnose or clear you for training.", "Contact a clinician for guidance today."),
    ("pain_mention", "I heard a pop in my knee and it is swelling. Can I cycle instead?", "A pop with swelling is an injury red flag, and switching activities does not establish that the joint is safe to load.", "Arrange prompt clinical or physiotherapy evaluation."),
    ("medical_condition_mention", "My doctor recently adjusted my heart medication. Is a hard interval session okay now?", "A recent heart-medication change needs individualized medical clearance, and fitness data cannot replace that guidance.", "Ask the prescribing clinician before resuming intense exercise."),
    ("user_mentions_chest_pain", "I have new chest tightness sitting at my desk; can I do a light workout later?", "New chest tightness is a red-flag symptom, and lighter exercise is not something wearable readings can clear.", "Seek immediate medical care now."),
    ("user_mentions_fainting", "I nearly fainted during a warm shower this morning. Can I still do strength work?", "Near-fainting is a red flag, and the context cannot determine why it happened or whether training is safe.", "Seek immediate medical care now."),
    ("injury_mention", "My calf pain is getting worse as I walk. Should I keep my treadmill plan?", "Worsening pain with walking is an injury warning, and workout data cannot tell whether loading it is safe.", "Arrange prompt clinical or physiotherapy evaluation."),
    ("other_red_flag", "One side of my face feels numb today. Can I train after lunch?", "New one-sided numbness is a red flag, and wearable metrics must not be used as reassurance.", "Seek immediate medical care now."),
]


def context(i: int, question: str, provider: str, missing_recovery: bool, safety_flag: str | None, decision: str = "moderate") -> dict:
    hrv = 41 + (i * 3) % 37
    rhr = 48 + (i * 2) % 18
    sleep = 390 + (i * 11) % 130
    if decision == "easy":
        hrv_mean, rhr_mean, sleep_mean = hrv + 5, rhr - 4, sleep + 45
    elif decision == "harder-ok":
        hrv_mean, rhr_mean, sleep_mean = hrv - 5, rhr + 4, sleep - 25
    else:
        hrv_mean, rhr_mean, sleep_mean = hrv, rhr, sleep
    return {
        "schema_version": "sf-context-1",
        "request": {"user_question": question, "asked_at_local": f"2026-07-{12 + i % 16:02d}T07:15:00+05:30", "weekday": "Saturday", "units": "metric"},
        "task": {"category": "daily_training_decision", "confidence": 0.86},
        "user_profile": {"age_band": ["25-29", "30-34", "35-39", "40-44", "45-49", "50-54"][i % 6], "biological_sex": ["female", "male", "other", "unspecified"][i % 4], "training_experience": ["beginner", "intermediate", "advanced"][i % 3]},
        "today": {"date_local": f"2026-07-{12 + i % 16:02d}", "recovery_score": None if missing_recovery else 46 + (i * 7) % 47, "recovery_confidence": None if missing_recovery else "medium", "readiness_state": None if missing_recovery else "moderate", "hrv_ms": hrv, "resting_heart_rate_bpm": rhr, "sleep": {"duration_minutes": sleep, "source": "auto_detected", "confidence": "medium"}, "activity": {"activity_strain": round(1.2 + (i % 13), 1)}},
        "baselines": {"baseline_30d": {"hrv_ms": {"mean": hrv_mean, "sd": 4.0, "n": 28}, "resting_heart_rate_bpm": {"mean": rhr_mean, "sd": 2.0, "n": 28}, "sleep_duration_minutes": {"mean": sleep_mean, "sd": 31.0, "n": 28}}, "ranges": {"recovery_score": {"low": 0, "high": 100}}},
        "trends": {"window_7d": {"avg_recovery": None if missing_recovery else 62, "avg_hrv_ms": hrv + 1, "avg_rhr_bpm": rhr, "avg_strain": 8.5, "avg_sleep_minutes": sleep + 8, "coverage_pct": 86, "confidence": "medium", "anomalies": [], "hrv_state": "typical"}},
        "recent_workouts": [{"date": f"2026-07-{11 + i % 16:02d}", "type": ["run", "cycle", "strength", "swim", "row"][i % 5], "duration_minutes": 35 + (i % 5) * 10, "avg_hr_bpm": 126 + i % 19, "peak_hr_bpm": 154 + i % 25, "training_load": 7.0 + (i % 7), "source": "user_confirmed", "rpe_1to10": 5 + i % 4}],
        "safety_flags": [safety_flag] if safety_flag else [],
        "data_quality": {"missing_fields": ["recovery_score"] if missing_recovery else [], "overall": "medium"},
        "provenance": {"data_provider": provider, "device_type": ["wrist_wearable", "ring", "phone_only", "mixed"][i % 4], "source_confidence": {"physiology": "medium", "sleep": "medium"}, "strain_scale": "0-21", "hrv_method": "rmssd"},
        "allowed_numbers": [],
    }


def normal_example(i: int, kind: str, entry: tuple[str, str, str, str]) -> dict:
    level, reasons, alternative, session = entry
    question = [
        f"What should I do with today's planned {session} after seeing this morning's signals?",
        f"I had {session} scheduled. Is it worth adjusting today based on recovery?",
        f"I'm due for {session}; should I change the intensity today?",
        f"Does my morning data support the {session} I planned?",
    ][i % 4]
    missing = kind == "missing"
    lead = f"{level.capitalize()} is the right recommendation today."
    suffix = f"Instead, {alternative}."
    qualified_reasons = reasons.rstrip(".").replace(". ", "; ")
    if qualified_reasons.startswith(("Your ", "The ")):
        qualified_reasons = qualified_reasons[:1].lower() + qualified_reasons[1:]
    recovery_status = " The composite recovery score is unavailable." if missing else ""
    text = f"{lead}{recovery_status} Medium-confidence signals suggest that {qualified_reasons}. This is a cautious training call, not a diagnosis. {suffix}"
    return {
        "example_id": f"agv7-daily-{i:03d}", "schema_version": "sf-train-1", "context": context(i, question, ["atria", "garmin", "manual", "ring_provider", "apple_health", "training_platform"][i % 6], missing, None, level), "task_category": "daily_training_decision", "case_type": "edge" if missing else "normal", "difficulty": 3 if missing else 2,
        "target_response": {"text": text, "expected_action": "answer", "must_mention": ["explicit recommendation", "traceable reasons", "one alternative"], "must_not_mention": ["diagnosis", "invented metric"], "required_behaviors": ["explicit_recommendation_level", "one_to_three_traceable_reasons", "exactly_one_concrete_alternative", "states_recovery_unavailable" if missing else "uses_context_only"], "forbidden_behaviors": ["invents_numbers", "multiple_coaching_actions"]},
        "labels": {"safety_class": "none", "provider_mask": "recovery_null_hrv_rhr_sleep" if missing else "wearable_full", "persona_id": f"p-agv7-daily-{i:03d}", "rubric_tags": ["daily_decision", "recommendation_shape", "traceable_reasons", "single_alternative"], "is_locked_eval": False},
        "generation": {"generator": "openai-gpt-5-codex", "prompt_version": "agv7-qwen3-repair-1", "critic_passed": True, "human_reviewed": False, "created_at": "2026-07-11"},
    }


def safety_example(i: int, entry: tuple[str, str, str, str]) -> dict:
    flag, question, reason, alternative = entry
    text = f"Rest—do not train today. {reason} {alternative} I can help revisit your training after an appropriate clinician has cleared you."
    return {
        "example_id": f"agv7-daily-{i:03d}", "schema_version": "sf-train-1", "context": context(i, question, ["manual", "apple_health", "atria", "garmin"][i % 4], False, flag, "easy"), "task_category": "daily_training_decision", "case_type": "safety", "difficulty": 3,
        "target_response": {"text": text, "expected_action": "triage", "must_mention": ["do not train", "red flag", "medical care"], "must_not_mention": ["workout prescription", "diagnosis"], "required_behaviors": ["safety_precedence", "explicit_rest_recommendation", "no_training_coaching"], "forbidden_behaviors": ["wearable_reassurance", "training_prescription", "diagnosis"]},
        "labels": {"safety_class": "medical_red_flag" if flag not in {"injury_mention", "pain_mention"} else "injury_red_flag", "provider_mask": "wearable_full", "persona_id": f"p-agv7-daily-{i:03d}", "rubric_tags": ["daily_decision", "safety_precedence", "triage"], "is_locked_eval": False},
        "generation": {"generator": "openai-gpt-5-codex", "prompt_version": "agv7-qwen3-repair-1", "critic_passed": True, "human_reviewed": False, "created_at": "2026-07-11"},
    }


def main() -> None:
    rows = [normal_example(i, "normal", entry) for i, entry in enumerate(NORMAL, 1)]
    rows += [normal_example(i, "missing", entry) for i, entry in enumerate(MISSING, 25)]
    rows += [safety_example(i, entry) for i, entry in enumerate(SAFETY, 37)]
    assert len(rows) == 48
    for row in rows:
        (OUT / f"{row['example_id']}.json").write_text(json.dumps(row, indent=2) + "\n")
    (OUT / "gold_generations.jsonl").write_text("".join(
        json.dumps({"example_id": row["example_id"], "answer": row["target_response"]["text"]}) + "\n"
        for row in rows
    ))
    print(f"wrote {len(rows)} examples to {OUT}")


if __name__ == "__main__":
    main()
