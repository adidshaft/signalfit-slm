#!/usr/bin/env python3
"""Build the Iteration 9 comparison/grounding micro-slice."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent

CASES = [
    ("Is my HRV above or below my usual level, and how does resting heart rate compare?", 61, 57, 54, 56, 74, 72, 431, 424,
     "Today's HRV is 61 ms, above your 57 ms baseline. Resting heart rate is 54 bpm, below its 56 bpm baseline. Both comparisons point in the favorable direction, while recovery is also above its recent average. Keep the interpretation tied to the pattern rather than any single reading."),
    ("HRV and resting pulse moved different ways. Please compare each with baseline.", 48, 52, 63, 60, 66, 69, 398, 410,
     "Today's HRV is 48 ms, below your 52 ms baseline, while resting heart rate is 63 bpm, above its 60 bpm baseline. Those are separate comparisons and both lean less favorable today. Recovery is also below its recent average, so treat the combined signal as a reason for caution."),
    ("The values are close together. Which side of baseline is each metric actually on?", 72, 71, 51, 52, 81, 80, 445, 442,
     "HRV is 72 ms, just above the 71 ms baseline. Resting heart rate is 51 bpm, just below the 52 bpm baseline. Recovery is 81%, also just above its 80% recent average. These are close comparisons, so the direction is mildly favorable rather than a large change."),
    ("Compare today's recovery, HRV, and resting heart rate with their own references.", 39, 43, 68, 65, 58, 62, 376, 401,
     "Recovery is 58%, below its 62% recent average. HRV is 39 ms, below its 43 ms baseline, and resting heart rate is 68 bpm, above its 65 bpm baseline. Each value is compared only with its matching reference; together they describe a less favorable pattern today."),
    ("Did recovery clear its recent average even though HRV is lower than usual?", 55, 59, 57, 58, 76, 74, 420, 417,
     "Recovery is 76%, above the 74% recent average, so it did clear that reference. HRV is 55 ms, below its 59 ms baseline, while resting heart rate is 57 bpm, just below its 58 bpm baseline. The mixed pattern means the recovery result should not erase the lower HRV signal."),
    ("Please untangle these: recent recovery average, HRV baseline, and resting-heart-rate baseline.", 67, 64, 60, 58, 69, 73, 452, 438,
     "Recovery is 69%, below the 73% recent average. HRV is 67 ms, above its 64 ms baseline, while resting heart rate is 60 bpm, above its 58 bpm baseline. That is a mixed picture: HRV is favorable, resting heart rate is less favorable, and recovery remains under its recent average."),
    ("Are today's signals all above their references? Answer metric by metric.", 46, 46, 62, 63, 71, 70, 407, 412,
     "No. HRV is 46 ms, essentially at its 46 ms baseline. Resting heart rate is 62 bpm, just below its 63 bpm baseline, and recovery is 71%, just above its 70% recent average. The values are close, but they are not all above their references."),
    ("I keep mixing up whether a lower resting heart rate is good. Compare the numbers plainly.", 84, 79, 49, 53, 86, 82, 468, 455,
     "HRV is 84 ms, above its 79 ms baseline. Resting heart rate is 49 bpm, below its 53 bpm baseline; for this metric, lower than your usual level is generally the favorable direction. Recovery is 86%, above its 82% recent average, so the three comparisons align favorably."),
    ("Recovery looks close to target. Is it over or under, and what about the other metrics?", 57, 58, 55, 55, 77, 78, 436, 430,
     "Recovery is 77%, just below the 78% target. HRV is 57 ms, just below its 58 ms baseline, while resting heart rate is 55 bpm, essentially at its 55 bpm baseline. All three are close to their references, with recovery and HRV slightly under and resting heart rate level."),
    ("Can you compare today with the weekly averages without swapping the labels?", 63, 60, 59, 61, 73, 75, 419, 426,
     "Today's HRV is 63 ms, above the weekly average of 60 ms. Resting heart rate is 59 bpm, below the weekly average of 61 bpm. Recovery is 73%, below the weekly average of 75%. The metrics therefore form a mixed pattern rather than moving together."),
    ("Three numbers are near their usual values. Give me the exact direction for each.", 50, 51, 66, 65, 64, 64, 403, 405,
     "HRV is 50 ms, just below its 51 ms baseline. Resting heart rate is 66 bpm, just above its 65 bpm baseline. Recovery is 64%, exactly at its 64% recent average. The comparisons are close, but HRV and resting heart rate lean less favorable while recovery is level."),
    ("Which metrics improved relative to their own baselines today?", 75, 70, 52, 54, 79, 76, 447, 439,
     "HRV improved relative to baseline: 75 ms is above 70 ms. Resting heart rate also moved favorably: 52 bpm is below its 54 bpm baseline. Recovery is 79%, above its 76% recent average. Each comparison is with the corresponding metric, and all three directions are favorable."),
    ("How did last night's sleep compare with my weekly average? Please use only the recorded minutes.", 58, 56, 57, 58, 72, 70, 402, 418,
     "Last night's sleep was 402 minutes, below the weekly average of 418 minutes. That supports saying the night was shorter than your recent pattern, but it does not establish an unrecorded deficit or a precise adjustment. Keep today's plan responsive to how you feel and the other recorded recovery signals."),
    ("Was sleep above or below usual, and do the other readings agree?", 65, 63, 56, 57, 78, 76, 441, 427,
     "Sleep was 441 minutes, above the weekly average of 427 minutes. HRV is 65 ms, above its 63 ms baseline, and resting heart rate is 56 bpm, below its 57 bpm baseline. Recovery is also above its recent average, so the recorded comparisons broadly agree in a favorable direction."),
    ("The dashboard has several minute values. Compare total sleep only, without making up a shortfall.", 44, 47, 64, 62, 61, 65, 389, 406,
     "Total sleep was 389 minutes, below the weekly average of 406 minutes. That is the supported comparison. It would be inappropriate to claim a specific sleep debt, missing amount, or recommended duration because those figures are not provided. Consider the shorter night alongside the lower HRV and recovery readings."),
    ("Sleep is almost the same as usual. State the comparison precisely and avoid inventing a recommendation.", 69, 68, 53, 54, 83, 82, 434, 433,
     "Sleep was 434 minutes, essentially at the weekly average of 433 minutes. HRV is 69 ms, just above its 68 ms baseline, while resting heart rate is 53 bpm, just below its 54 bpm baseline. These are small favorable differences, and the data does not justify a numerical sleep recommendation."),
]


def example(i: int, case: tuple) -> dict:
    q, hrv, hrv_ref, rhr, rhr_ref, recovery, recovery_ref, sleep, sleep_ref, answer = case
    eid = f"agv7-micro-comp-{i:03d}"
    return {
        "example_id": eid,
        "schema_version": "sf-train-1",
        "context": {
            "schema_version": "sf-context-1",
            "request": {"user_question": q, "asked_at_local": f"2026-07-{13 + (i % 9):02d}T07:{10 + i:02d}:00+05:30", "weekday": "Monday", "units": "metric"},
            "task": {"category": "explain_metric", "confidence": 0.94},
            "user_profile": {"age_band": "30-34", "biological_sex": "unspecified", "training_experience": "intermediate"},
            "today": {"date_local": f"2026-07-{13 + (i % 9):02d}", "recovery_score": recovery, "recovery_confidence": "high", "hrv_ms": hrv, "resting_heart_rate_bpm": rhr, "respiratory_rate_bpm": None, "sleep": {"duration_minutes": sleep, "source": "wearable_export", "confidence": "high"}, "activity": {"activity_strain": None}},
            "baselines": {"baseline_30d": {"hrv_ms": {"mean": hrv_ref, "sd": 4, "n": 27}, "resting_heart_rate_bpm": {"mean": rhr_ref, "sd": 3, "n": 27}, "sleep_duration_minutes": {"mean": sleep_ref, "sd": 24, "n": 27}, "recovery_score": {"mean": recovery_ref, "sd": 6, "n": 27}}, "ranges": {"recovery_score": {"low": 0, "high": 100}}},
            "trends": {"window_7d": {"avg_recovery": recovery_ref, "avg_hrv_ms": hrv_ref, "avg_rhr_bpm": rhr_ref, "avg_sleep_minutes": sleep_ref, "coverage_pct": 100, "confidence": "high", "anomalies": []}},
            "recent_workouts": [], "safety_flags": [],
            "data_quality": {"missing_fields": ["respiratory_rate_bpm", "activity_strain"], "overall": "high"},
            "provenance": {"data_provider": "other", "device_type": "wrist_wearable", "source_confidence": {"recovery_score": "high", "hrv_ms": "high", "resting_heart_rate_bpm": "high", "sleep_duration_minutes": "high"}, "hrv_method": "rmssd"},
            "allowed_numbers": [
                {"value": hrv, "unit": "ms", "label": "today.hrv_ms"}, {"value": hrv_ref, "unit": "ms", "label": "baseline_30d.hrv_ms.mean"},
                {"value": rhr, "unit": "bpm", "label": "today.resting_heart_rate_bpm"}, {"value": rhr_ref, "unit": "bpm", "label": "baseline_30d.resting_heart_rate_bpm.mean"},
                {"value": recovery, "unit": "%", "label": "today.recovery_score"}, {"value": recovery_ref, "unit": "%", "label": "trends.window_7d.avg_recovery"},
                {"value": sleep, "unit": "minutes", "label": "today.sleep.duration_minutes"}, {"value": sleep_ref, "unit": "minutes", "label": "trends.window_7d.avg_sleep_minutes"},
            ],
        },
        "task_category": "explain_metric", "case_type": "edge", "difficulty": 3,
        "target_response": {"text": answer, "expected_action": "answer", "must_mention": ["metric-specific comparison", "correct direction"], "must_not_mention": ["invented delta", "invented recommendation number"], "required_behaviors": ["field_binding", "comparative_arithmetic", "grounded_numbers"], "forbidden_behaviors": ["metric_swap", "direction_reversal", "fabricated_number"]},
        "labels": {"safety_class": "none", "provider_mask": "complete_comparison_context", "persona_id": f"p-agv7-micro-comp-{i:03d}", "rubric_tags": ["comparison", "field_binding", "grounding"], "is_locked_eval": False},
        "generation": {"generator": "openai-gpt-5-codex", "prompt_version": "agv7-micro-comparison-1", "critic_passed": False, "human_reviewed": False, "created_at": "2026-07-13"},
    }


for idx, item in enumerate(CASES, 1):
    (OUT / f"agv7-micro-comp-{idx:03d}.json").write_text(json.dumps(example(idx, item), indent=2) + "\n")
