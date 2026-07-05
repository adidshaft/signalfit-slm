# SignalFit Universal Schema Design (v0.1 draft)

Status: analysis-only draft, 2026-07-05. All Atria facts below were verified by
reading the Atria codebase (read-only). Anything not verified is marked
**assumption** or **future**.

---

## 1. Atria as reference data provider — verified field inventory

Source of truth files inspected:

- `Atria/Atria/Sessions.swift` — `SavedSession`, `DailyRollup`, `SavedDailyMetric`,
  `UserConfirmedWorkout`, `UserConfirmedSleep`, `SleepStageKind/Evidence/Segment`,
  `BehaviorJournalEntry`, `TrendSummary`, `TrainingLoadSummary`,
  `TodayHRZoneMinutes`, `VO2MaxEstimateSummary`, `BiologicalAgeSummary`,
  `WorkoutReadiness`
- `Atria/Atria/DailyRollupStore.swift` — `DailyRollupStoreEntry`, `DailyRollupVitals`
- `Atria/Atria/AtriaAICoach.swift` — `AtriaCoachPayload` (existing AI context +
  fabrication check)
- `Atria/Atria/HRV.swift` — `HRVSnapshot` (RMSSD/SDNN/pNN50/lnRMSSD + artifact gates)
- `Atria/Atria/AtriaJournalStore.swift` — typed journal questions
- `Atria/Atria/AtriaNutritionContext.swift` — `AtriaNutritionSummary` (HealthKit read)
- `Atria/Atria/AtriaSleepBudget.swift` — sleep need / debt / performance math
- `Atria/Atria/AtriaCycleTracking.swift`, `AtriaStressMonitor.swift`,
  `AtriaMetricTargets.swift`, `Metrics.swift`, `Insights.swift` (`AthleteProfile`)
- `docs/export-schema.md` — research bundle + raw export (hr.csv, rr.csv,
  sleeps.json, workouts.json, rollups.json)

### 1a. Raw wearable/app data (verified)

| Atria field/source | SignalFit generic name | Source file/type | Type | Example | Update freq | AI reliability | Version |
|---|---|---|---|---|---|---|---|
| `SavedSession.points [(t,bpm)]` | (not sent to model raw; feeds calculated) | Sessions.swift | [[s, int]] | `[12.3, 62]` | ~1 Hz live | High (accepted-sample gated) | deferred (aggregates only) |
| `SavedSession.rrPoints [(t,ms)]` | (feeds `hrv_ms`) | Sessions.swift | [[s, int]] | `[12.9, 940]` | per beat | High after artifact gates | deferred |
| Strap battery | `device_battery_pct` (metadata only) | AtriaBLEManager.swift / docs 01-overview | int | 78 | live | High | V2 (metadata) |
| `motionHint*`, `motionShort*` (0x32 packets) | — | Sessions.swift | ints/doubles | — | live | **Unvalidated — excluded** | never (until validated) |
| `imu*` fields (0x33 frames) | — | Sessions.swift (`imuValidationState`) | mixed | — | live | **Unvalidated research — excluded** | never (until validated) |
| `strapStepResearch*` | `steps` (future) | Sessions.swift | int | 8421 | daily | **Unvalidated research — excluded** | V2 gated |
| `spo2ResearchCandidateFrames`, `skinTempResearch*` | `spo2_pct`, `skin_temp_deviation_c` (future) | Sessions.swift | int | — | nightly | **Unvalidated — excluded** | V2 gated |

### 1b. Calculated metrics (verified)

| Atria field | SignalFit generic name | Source | Type | Example | Freq | Reliability | Version |
|---|---|---|---|---|---|---|---|
| `SavedDailyMetric.recoveryPercent` / `DailyRollupStoreEntry.recovery` | `recovery_score` | Sessions.swift / DailyRollupStore.swift | int 0–100, nullable | 68 | daily | High once baseline learned; carries `recoveryConfidence`. Logistic personal z-score model (`AtriaAnalytics.Recovery.estimate`); weights renormalize at reduced confidence when sleep is missing | **MVP** |
| `Recovery.Estimate.Confidence` (learning/unverified/personal baseline/validated) | `recovery_confidence` (adapter maps: validated→high, personal baseline→medium, unverified→low, learning→learning) | AtriaAnalytics.swift | enum | "personal baseline" | daily | High | **MVP** |
| `Recovery.Estimate.Contributor` (kind hrv/restingHeartRate/sleep/respiration, zScore, weight, direction) | `today.recovery_contributors[]` | AtriaAnalytics.swift | array | `{factor:"hrv", z_score:-1.2, weight:0.5, direction:-1}` | daily | High — provider-computed, ideal grounding for recovery_explanation | V1 |
| `Coach.baseStrainTarget/liveStrainTarget` (recovery≤33→9, ≥67→17, linear between; live decay 0.10×strain) | `today.activity.strain_target` | Dashboard.swift | double | 12.0 | live/daily | High (deterministic) | V1 |
| `AtriaAnalytics.TargetZones.sleepEfficiency` (green ≥90%, yellow ≥80%) | `sleep.efficiency_pct` | AtriaAnalytics.swift | double 0–1 → int % | 91 | daily | High — computed natively, not just derivable | V1 |
| `WeeklyPlan` (targets: bedtimeConsistency/workoutCount/rhrInRange with goal+current, from 28d rollups) | `plan_context.weekly_targets[]` | AtriaWeeklyPlan.swift | array | bedtime goal 5 nights, current 3 | weekly | High | V2 |
| `AtriaAnalytics.RespRateRsa.estimate` (RSA from resampled RR @4Hz) | (source of `respiratory_rate_bpm`) | AtriaAnalytics.swift | double | 14.8 | nightly | Medium-high | V1 |
| `HRVSnapshot.rmssd` / session `hrv` | `hrv_ms` | HRV.swift / Sessions.swift | int ms | 52 | per session + daily rollup (`lnRMSSD`) | High (artifact-gated; `hrvReferenceValidated` flag exists) | **MVP** |
| `HRVSnapshot.sdnn` | `hrv_sdnn_ms` (metadata) | HRV.swift | double | 61.2 | per session | Medium | V2 |
| `DailyRollupStoreEntry.rhr` / `restingHR` | `resting_heart_rate_bpm` | DailyRollupStore/Sessions | int | 55 | daily | High | **MVP** |
| `respiratoryRate` (from RR modulation) | `respiratory_rate_bpm` | Sessions/DailyRollupStore | double | 14.8 | nightly/daily | Medium-high | V1 |
| `sleepSeconds`, `UserConfirmedSleep.duration` | `sleep_duration_minutes` | Sessions/DailyRollupStore | double→int | 432 | daily | High (user-confirmed) | **MVP** |
| `sleepPerformance` (slept/needed) | `sleep_performance_pct` | DailyRollupStore + AtriaSleepBudget | int 0–100 | 88 | daily | High | V1 |
| `AtriaSleepBudget.sleepNeed/sleepDebt` | `sleep_need_minutes`, `sleep_debt_minutes` | AtriaSleepBudget.swift | double | 486 / 63 | daily | High (deterministic formula) | V1 |
| `sleepConsistencyPercent` | `sleep_consistency_pct` | Sessions.swift | int | 74 | daily | Medium | V1 |
| `bedtimeMinutes` | `bedtime_local_minutes` | DailyRollupStore.swift | int 0–1440 | 1395 | daily | High | V1 |
| `stageSegments` (awake/light/rem/sws/deep) | `sleep_stages_minutes` | Sessions.swift | map | `{light:210, deep:80, rem:95, awake:25}` | nightly | Depends on `SleepStageEvidence` (none/manualEstimate/sensorResearch/validated) — include evidence | V1 (with evidence label) |
| `strain` (Banister TRIMP / Edwards, 0–21) | `activity_strain` | Metrics.swift / Sessions | double 0–21 | 12.4 | continuous/daily | High (validated math, WHOOP-style scale — scale documented in provenance) | **MVP** |
| `TrainingLoadSummary.acuteLoad/chronicLoad/ratio/monotony` | `training_load` (acute_7d, chronic_28d, acwr, monotony) | Sessions.swift | doubles | 34.2 / 40.1 / 0.85 / 1.6 | daily | High after 14 strain days (`confidence:"learning"` before) | V1 |
| `TodayHRZoneMinutes` | `hr_zone_minutes` | Sessions.swift | ints | `{z2:24, z3:11}` | daily | High | V1 |
| `activeCalories` + `caloriesConfidence` (Keytel) | `active_calories_kcal` + confidence | Sessions.swift | double | 512 | per session/day | Medium (estimate, never measured) | V1 |
| `VO2MaxEstimateSummary.value` | `vo2max_estimate` | Sessions.swift | double | 46.5 | slow-moving | Medium (own confidence field) | V2 |
| `BiologicalAgeSummary` / `fitnessAgeDelta` | `fitness_age_delta_years` | Sessions/AtriaFitnessAge/DailyRollupStore | int | -3 | daily after 28d | Medium | V2 |
| `AtriaStressLevel` (calm/low/medium/high) | `stress_level` | AtriaStressMonitor.swift | enum | "low" | live/daily | Medium | V1 |
| `TrendSummary` (7/30/90/180d avgs + anomalies + hrvState) | `trends.window_7d/30d` | Sessions.swift | struct | avgRecovery 64 | daily | High (has coverage % + confidence) | **MVP** (7d/30d) |
| `DailyRollupVitals` (rhr/hrv/resp mean, sd, n) | `baseline_7d` / `baseline_30d` | DailyRollupStore.swift | stats | `{mean:54.1, sd:2.9, n:28}` | daily | High | **MVP** (30d), V1 (7d) |
| `AtriaCoachPayload.baselines [String: VitalRange]` | `baselines` (low/high ranges) | AtriaAICoach.swift | map | `recovery: 0–100` | per request | High | **MVP** |
| `AtriaNapRecovery.adjustedRecovery` | `recovery_nap_adjusted` (metadata) | AtriaSleepBudget.swift | int | 72 | event | High | V2 |
| `WorkoutReadiness` gates (p90/p95/p99, coverage, contact quality) | (adapter-side QC only) | Sessions.swift | struct | — | per session | High for QC | not in model context |

### 1c. User-entered data (verified)

| Atria field | SignalFit generic name | Source | Type | Example | Freq | Reliability | Version |
|---|---|---|---|---|---|---|---|
| `AthleteProfile.biologicalSex` (male/female/unspecified) | `user_profile.biological_sex` | Insights.swift | enum | "female" | static | High | **MVP** |
| `AthleteProfile` birth year → age (banded in export) | `user_profile.age_years` or `age_band` | Insights.swift / export-schema.md | int / "30-34" | 31 | static | High | **MVP** |
| weight / heightCm | `weight_kg`, `height_cm` | AtriaSettingsView/Onboarding | double | 76.2 / 180 | static | High | V1 |
| `maxHR` + source (ageEstimate/measured) | `max_hr_bpm` + `max_hr_source` | AthleteProfile / AtriaMaxHRSuggestion | int + enum | 188, "measured" | static | High | V1 |
| `UserConfirmedWorkout` (label, avgHR, peakHR, p95/p99, strain, kcal, zoneSeconds, activityType, exerciseNames) | `workout_sessions[]` | Sessions.swift | struct | Run, 42 min, avg 148 | per workout | High (user-confirmed) | **MVP** (subset), V1 (full) |
| `UserConfirmedSleep` (+ confidence, source) | `sleep` block | Sessions.swift | struct | — | nightly | High | **MVP** |
| Strength sets (`strengthSets`, `LoggedSet`, exercise catalog) | `workout_sessions[].sets[]` | Sessions/AtriaStrengthLog | array | Squat 5×5 @100kg | per workout | High | V2 |
| `BehaviorJournalEntry.tags` (sleep/alcohol/caffeine/protein/training/stress) + `healthAutoTags` | `journal_entries[].tags` | Sessions.swift | enum array | ["alcohol","stress"] | daily | High (self-report) | V1 |
| Typed journal: `caffeine.lastTime` (timeOfDayMinutes), `alcohol.drinks` (quantity), `mood.scale` (1–5), `stress.scale` (1–5) | `journal_entries[]` typed answers; `subjective.mood_1to5`, `subjective.stress_1to5` | AtriaJournalStore.swift | typed values | mood 4 | daily | High (self-report) | V1 |
| Cycle tracking (opt-in): period entries, phase (menstrual/follicular/ovulatory/luteal), confidence (estimating/personalized) | `cycle` block (optional) | AtriaCycleTracking.swift | enum + int | "luteal", day 21 | daily | Medium ("estimate", never fact) | V2 |
| Nutrition via HealthKit: kcal, proteinG, carbsG, fatG, waterMl, caffeineMg, lastCaffeineHour, alcoholDrinks | `nutrition` block | AtriaNutritionContext.swift | doubles | 2150 kcal, 130 g protein | daily | Medium (depends on user logging) | V1 |
| `AtriaMetricTarget` (green/yellow/red bands, goal, direction, source) | `goals.target_metrics[]` | AtriaMetricTargets.swift | struct | recovery green ≥67 | static/edited | High | V1 |

### 1d. Inferred analytics (verified)

| Atria source | SignalFit generic name | Reliability | Version |
|---|---|---|---|
| `BehaviorCorrelationSummary`, `AtriaBehaviorImpact`, `AtriaJournalInsights` | `habit_insights[]` (precomputed correlation strings) | Medium — correlational, small n | V2 |
| `AtriaInsight` (recovery/hrv), `AtriaHighlights`, weekly/monthly reports | `provider_insights[]` (optional metadata) | Medium | V2 |
| `Coach.Guidance` strain target, `AtriaWeeklyPlan` | `plan_context` (today's target, weekly plan) | Medium-high | V1 (target), V2 (plan) |
| `TrendSummary.anomalies` + `hrvState` | `trends.*.anomalies[]`, `hrv_state` | High (has sample-day counts) | V1 |

### 1e. Missing but useful (not in Atria today — assumptions/future)

- Validated **steps** (only unvalidated strap-step research exists) → `steps` V2-gated.
- GPS distance/pace/elevation — **assumption: absent** (no GPS code found in files inspected).
- Validated SpO2, skin temperature — research candidates only.
- Subjective **energy** and **soreness** ratings (mood/stress exist; energy/soreness do not) → schema reserves them.
- Workout **RPE** — not found.
- Body-weight trend over time (single profile weight only).
- Menstrual-cycle-aware recovery adjustment (phase exists; no metric coupling).
- Timezone-travel context (per-day `tzOffsetMinutes` exists in rollups — small implementation to expose).

### 1f. Unsafe/unvalidated — must NOT enter model context

Everything Atria itself gates behind research flags: IMU features (`imuValidationState`),
motion hints, strap-step research, sleep/wake research state, SpO2/skin-temp candidate
frames, HRV values that fail `hrvReferenceValidated`/continuity gates, sessions with
`contactCompromised == true` or `rrDisagreement == true`. The Atria→SignalFit adapter
must filter these; the schema's `source_confidence` never carries "research" grade data.

---

## 2. Canonical SignalFit context schema (universal)

Canonical JSON, `schema_version: "sf-context-1"`. Full machine-readable version in
`schemas/assistant_context.schema.json`. Shape summary (● = required in MVP,
○ = optional):

```jsonc
{
  "schema_version": "sf-context-1",              // ● string — versioning
  "request": {
    "user_question": "Should I train hard today?", // ● string — the query
    "asked_at_local": "2026-07-05T07:45:00+02:00", // ● ISO local — "today" anchoring (Atria: AtriaCoachPayload.now)
    "weekday": "Saturday",                         // ○ (Atria: payload.weekday)
    "units": "metric"                              // ○ metric|imperial (Atria: payload.units)
  },
  "task": {                                        // training label / router hint
    "category": "daily_training_decision",         // ● enum (see §5)
    "confidence": 0.92                             // ○ classifier confidence
  },
  "user_profile": {                                // source: user input
    "age_band": "30-34",                           // ● (Atria banding math, export-schema.md)
    "biological_sex": "female",                    // ● male|female|other|unspecified
    "height_cm": 172, "weight_kg": 64.0,           // ○ V1 (AthleteProfile)
    "max_hr_bpm": 188, "max_hr_source": "measured",// ○ V1
    "training_experience": "intermediate"          // ○ V2 — future (not in Atria)
  },
  "goals": {                                       // source: user input
    "primary_goal": "improve_recovery",            // ○ V1 free/enum
    "target_metrics": [                            // ○ V1 (AtriaMetricTarget)
      {"metric": "recovery_score", "green_at": 67, "direction": "higher_is_better", "source": "personal_baseline"}
    ],
    "preferences": ["morning_workouts"]            // ○ V2 — future
  },
  "today": {
    "date_local": "2026-07-05",                    // ●
    "recovery_score": 68,                          // ● 0–100 | null (calculated)
    "recovery_confidence": "high",                 // ● when score present
    "readiness_state": "moderate",                 // ○ derived bucket low|moderate|high (calculable)
    "hrv_ms": 52,                                  // ● int | null (RMSSD; calculated)
    "resting_heart_rate_bpm": 55,                  // ● int | null
    "respiratory_rate_bpm": 14.8,                  // ○ V1
    "stress_level": "low",                         // ○ V1 calm|low|medium|high (AtriaStressLevel)
    "sleep": {
      "duration_minutes": 432,                     // ● | null
      "need_minutes": 486, "debt_minutes": 63,     // ○ V1 (AtriaSleepBudget)
      "performance_pct": 88,                       // ○ V1
      "efficiency_pct": 91,                        // ○ V1 (calculable: duration/span)
      "consistency_pct": 74,                       // ○ V1
      "bedtime_local": "23:15", "waketime_local": "06:42", // ○ V1
      "stages_minutes": {"awake": 25, "light": 210, "rem": 95, "deep": 80}, // ○ V1
      "stage_evidence": "sensor_estimate",         // ○ required with stages: none|manual_estimate|sensor_estimate|validated
      "source": "auto_detected", "confidence": "high", // ○ V1
      "naps": [{"duration_minutes": 40}]           // ○ V2
    },
    "activity": {
      "activity_strain": 4.1,                      // ● double | null — 0–21 scale, scale noted in provenance
      "strain_target": 12.0,                       // ○ V1 (Coach.Guidance target)
      "hr_zone_minutes": {"rest": 640, "warmup": 22, "fat_burn": 24, "aerobic": 11, "anaerobic": 3, "max": 0}, // ○ V1
      "active_calories_kcal": 512,                 // ○ V1 (+ estimate confidence)
      "active_calories_confidence": "estimate",
      "steps": null                                // ○ V2 — provider-dependent; Atria: unvalidated → null
    },
    "subjective": {                                // source: user input
      "mood_1to5": 4, "stress_1to5": 2,            // ○ V1 (typed journal)
      "energy_1to5": null, "soreness_1to5": null   // ○ V2 — future (reserved)
    },
    "nutrition": {                                 // ○ V1 (HealthKit-sourced in Atria)
      "kcal": 2150, "protein_g": 130, "carbs_g": 240, "fat_g": 70,
      "water_ml": 1900, "caffeine_mg": 140, "last_caffeine_local_hour": 15, "alcohol_drinks": 0
    },
    "journal_flags": ["late_caffeine"]             // ○ V1 (behavior tags + auto tags)
  },
  "baselines": {                                   // calculated; keys are metric names
    "baseline_7d":  {"hrv_ms": {"mean": 54.0, "sd": 4.1, "n": 7}},   // ○ V1
    "baseline_30d": {"hrv_ms": {"mean": 55.2, "sd": 5.0, "n": 28},   // ● at least one metric
                     "resting_heart_rate_bpm": {"mean": 54.1, "sd": 2.9, "n": 28}},
    "ranges": {"recovery_score": {"low": 0, "high": 100}, "activity_strain": {"low": 0, "high": 21}} // ● scale guards
  },
  "trends": {
    "window_7d":  {"avg_recovery": 64, "avg_hrv_ms": 51, "avg_rhr_bpm": 56,
                   "avg_strain": 10.2, "avg_sleep_minutes": 415,
                   "coverage_pct": 86, "confidence": "high",
                   "anomalies": ["hrv_below_baseline_3d"], "hrv_state": "suppressed"}, // ● (Atria TrendSummary)
    "window_30d": { "...": "same shape" }          // ● when history allows
  },
  "training_load": {                               // ○ V1 (TrainingLoadSummary)
    "acute_load_7d": 34.2, "chronic_load_28d": 40.1,
    "acwr": 0.85, "monotony": 1.6,
    "acwr_signal": "good", "monotony_signal": "watch",
    "confidence": "high"
  },
  "recent_workouts": [                             // ● MVP: last ≤7, compact
    {"date": "2026-07-04", "type": "run", "duration_minutes": 42,
     "avg_hr_bpm": 148, "peak_hr_bpm": 176, "training_load": 8.9,
     "active_calories_kcal": 410, "source": "user_confirmed"}
  ],
  "journal_entries": [                             // ○ V1 (last ≤7 days)
    {"date": "2026-07-04", "tags": ["alcohol"], "alcohol_drinks": 2, "mood_1to5": 3}
  ],
  "cycle": {                                       // ○ V2, opt-in only (AtriaCycleTracking)
    "phase_estimate": "luteal", "day_of_cycle": 21, "confidence": "personalized"
  },
  "habit_insights": [                              // ○ V2 (provider-computed correlations)
    {"text": "Recovery averages 12 pts lower after alcohol days", "sample_days": 9, "confidence": "medium"}
  ],
  "safety_flags": [],                              // ● array of enum strings, e.g.
                                                   //   "user_mentions_chest_pain", "rhr_spike_vs_baseline",
                                                   //   "possible_illness_pattern", "extreme_weight_loss_request",
                                                   //   "ped_request", "injury_mention", "overtraining_pattern"
  "data_quality": {
    "missing_fields": ["respiratory_rate_bpm", "steps"], // ● explicit gaps
    "degraded_fields": [{"field": "sleep_stages_minutes", "reason": "sensor_estimate"}], // ○
    "overall": "medium"                            // ● high|medium|low
  },
  "provenance": {
    "data_provider": "atria",                      // ● e.g. whoop|apple_health|garmin|oura|fitbit|ultrahuman|manual|atria|other
    "device_type": "hr_strap",                     // ○ generic class, not model name
    "source_confidence": {                         // ● per-block: high|medium|low
      "recovery_score": "high", "sleep_stages_minutes": "medium"
    },
    "strain_scale": "0-21",                        // ○ documents provider scale
    "provider_metadata": {}                        // ○ ONLY place device-specific fields may appear
  },
  "allowed_numbers": [                             // ● fabrication guard (generalizes
    {"value": 68, "unit": "%", "label": "recovery_score"},   //  AtriaCoachPayload.serializedNumbers)
    {"value": 52, "unit": "ms", "label": "hrv_ms"}
  ]
}
```

**Why each top-level block matters** (condensed): `request` anchors time so "today"
is unambiguous; `task` routes behavior and is the training label; `user_profile`
personalizes intensity/HR-zone talk; `goals` lets answers point at the user's own
targets; `today` is the decision surface; `baselines`+`trends` let the model say
"below *your* normal" instead of population claims; `training_load` powers
plan/overtraining reasoning; `recent_workouts`/`journal_entries` explain *why* a
metric moved; `subjective` catches feel-vs-data mismatches; `safety_flags` triggers
the safety policy; `data_quality.missing_fields` powers insufficient_data_followup;
`provenance` keeps the model honest about source quality; `allowed_numbers` is the
anti-hallucination contract — any number in the answer must appear here (±1.0
tolerance, mirroring Atria's `fabricationFlags`).

---

## 3. Universal schema vs Atria — availability matrix

| Schema field | Atria status |
|---|---|
| request.* | **available** (AtriaCoachPayload now/weekday/units) |
| task.category | **needs small implementation** (no classifier; rule-based router possible) |
| user_profile age/sex | **available** (AthleteProfile + banding) |
| height/weight/max_hr | **available** |
| training_experience | **defer** (not collected) |
| goals.target_metrics | **available** (AtriaMetricTarget) |
| goals.primary_goal / preferences | **needs small implementation** (UI to ask) |
| today.recovery_score + confidence | **available** |
| today.readiness_state bucket | **calculable** (thresholds exist in AtriaMetricTarget) |
| hrv_ms / resting_heart_rate_bpm | **available** |
| respiratory_rate_bpm | **available** |
| stress_level | **available** (AtriaStressMonitor) |
| sleep duration/performance/need/debt/consistency/bedtime | **available** |
| sleep efficiency_pct | **available** (TargetZones.sleepEfficiency computes it natively) |
| today.recovery_contributors | **available** (Recovery.Estimate.Contributor: factor, z-score, weight, direction) |
| plan_context.weekly_targets | **available** (WeeklyPlan.generate from 28d rollups) — V2 schema anyway |
| sleep stages + evidence | **available** (evidence enum exists) |
| activity_strain + strain_target | **available** (strain; target via Coach.Guidance) |
| hr_zone_minutes | **available** (TodayHRZoneMinutes) |
| active_calories + confidence | **available** |
| steps | **defer** (research-gated, unvalidated) |
| subjective mood/stress | **available** (typed journal) |
| subjective energy/soreness | **needs small implementation** (add 2 typed questions) |
| nutrition block | **available** (HealthKit read, optional) |
| journal_flags / journal_entries | **available** (tags + typed answers) |
| baseline_7d/30d stats | **available** (DailyRollupVitals mean/sd/n; TrendSummary windows) |
| trends 7d/30d + anomalies | **available** (TrendSummary) |
| training_load ACWR/monotony | **available** (TrainingLoadSummary) |
| recent_workouts | **available** (UserConfirmedWorkout) |
| cycle | **available, opt-in** (AtriaCycleTracking; estimate-labeled) |
| habit_insights | **available** (BehaviorCorrelationSummary et al.) — V2 anyway |
| safety_flags | **needs small implementation** (adapter-side rules; inputs all exist: RHR spike vs baseline, anomalies, journal stress) |
| data_quality.missing_fields | **calculable** (nullability is pervasive; adapter enumerates nulls) |
| provenance.source_confidence | **calculable** (map Atria's per-metric confidence enums) |
| allowed_numbers | **available pattern** (AtriaCoachPayload.serializedNumbers — generalize) |
| vo2max / fitness_age (V2) | **available** (has own confidence/blockers) |
| spo2 / skin temp (V2) | **major implementation** (validation gates not passed) |

---

## 4. Three schema versions

**MVP** (synthetic data + first local training run) — required core only:
`schema_version, request(user_question, asked_at_local), task.category,
user_profile(age_band, biological_sex), today(date_local, recovery_score,
recovery_confidence, hrv_ms, resting_heart_rate_bpm, sleep.duration_minutes,
activity.activity_strain), baselines(baseline_30d for hrv+rhr, ranges),
trends.window_7d, recent_workouts(≤3 compact), safety_flags, data_quality
(missing_fields, overall), provenance(data_provider, source_confidence),
allowed_numbers`. Everything nullable; ~40 leaf fields; fits small-model context
easily. Atria can already fill 100% of MVP.

**V1** (production, Atria-supportable now/soon) — MVP plus: respiratory rate, stress
level, full sleep block (need/debt/performance/efficiency/consistency/bedtime/stages
+evidence), strain_target, hr_zone_minutes, active_calories, subjective mood/stress,
nutrition, journal_entries, goals.target_metrics, baseline_7d, trends.window_30d,
training_load, weight/height/max_hr, task.confidence, degraded_fields. Atria gaps:
task classifier, safety-flag rules, goal capture — all small implementations.

**V2** (future personalization) — V1 plus: cycle (opt-in), vo2max_estimate,
fitness_age_delta_years, steps (once validated), spo2/skin-temp (once validated),
strength sets in workouts, naps, energy/soreness ratings, workout RPE,
habit_insights, plan_context (weekly plan), preferences, multi-provider merge
(provenance becomes an array), travel/timezone context, body-weight trend.

---

## 5. Assistant task categories

| Category | Needs in context | Answer must contain | Must avoid |
|---|---|---|---|
| `explain_metric` | the metric value + its baseline/range + source_confidence | plain-language meaning, the user's value vs *their* baseline, confidence caveat | population norms stated as personal facts; clinical interpretation |
| `daily_training_decision` | recovery, hrv, rhr, sleep, strain(+target), training_load, recent_workouts | a clear go/moderate/easy recommendation, 1–3 data reasons, one concrete option | prescribing through pain/illness; absolute commands; ignoring safety_flags |
| `recovery_explanation` | recovery + trends + journal/nutrition/subjective for candidate causes | likely contributors ranked, framed as correlation ("often lines up with"), what to try tonight | asserting causation; inventing contributors not in data |
| `sleep_coaching` | sleep block + debt/need + bedtime history + caffeine/alcohol flags | 1–2 specific behaviors tied to the user's actual pattern, realistic target | sleep-disorder diagnosis; medication advice; shaming |
| `plan_adjustment` | training_load (acwr/monotony), trends, goals, recent_workouts | concrete adjustment (volume/intensity/rest-day), tied to ACWR/monotony signals, respecting confidence:"learning" | precise multi-week periodization from thin data; overriding pain signals |
| `goal_coaching` | goals, trends 30d, baselines | progress vs the user's own target bands, next milestone, realistic timeline language | guarantees of outcomes; body-composition promises |
| `habit_pattern_analysis` | journal_entries, habit_insights, trends | pattern with sample size ("in 9 logged days…"), honest correlation framing | causal claims; patterns from n<3; moralizing |
| `safety_triage` | safety_flags + whatever data triggered them | acknowledge, stop coaching, plain advice to seek appropriate care, no metric spin | reassurance that data "looks fine" despite red-flag symptom; diagnosis; urgency minimization |
| `insufficient_data_followup` | data_quality.missing_fields | say what's missing, why it matters, one question or logging suggestion | answering anyway with invented numbers; long interrogations |
| `refusal_or_redirect` | question text (PEDs, ED, medical, off-domain) | brief refusal, why, safer adjacent help if any | lectures; partial compliance; medical/pharma dosing detail |

---

## 6. Provider coverage pressure-test (ASSUMPTION-GRADE)

Everything in this section is from general ecosystem knowledge, **not verified
against provider API docs** — verify each column before writing an adapter. Its
purpose here is schema validation: does `sf-context-1` hold up beyond Atria?

Legend: ✓ expected available · ~ partial/derivable · ✗ absent (→ null + missing_fields)

| Schema field | Atria (verified) | WHOOP API | Apple Health | Garmin | Oura | Fitbit | Ultrahuman | Manual logs |
|---|---|---|---|---|---|---|---|---|
| recovery_score | ✓ | ✓ (recovery) | ✗ | ~ (body battery ≠ same scale) | ~ (readiness) | ~ (daily readiness) | ~ (dynamic recovery) | ✗ |
| hrv_ms | ✓ RMSSD | ✓ RMSSD | ✓ SDNN(!) | ✓ | ✓ RMSSD | ✓ | ✓ | ~ |
| resting_heart_rate_bpm | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ |
| respiratory_rate_bpm | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| sleep duration/stages/efficiency | ✓ | ✓ | ✓ (stages vary by source) | ✓ | ✓ | ✓ | ✓ | ~ duration only |
| sleep need/debt | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ | ✗ |
| activity_strain (0–21) | ✓ | ✓ | ✗ (derive TRIMP from HR?) | ~ (training load, different scale) | ✗ | ~ (AZM) | ✗ | ✗ |
| training_load acwr/monotony | ✓ | ✗ (derivable) | ✗ | ✓ (acute/chronic native) | ✗ | ✗ | ✗ | ✗ |
| hr_zone_minutes | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ (AZM) | ~ | ✗ |
| steps | ✗ (research-gated) | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ |
| active_calories | ✓ (estimate) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| workouts | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ~ | ✓ |
| subjective mood/stress | ✓ | ~ (journal) | ✓ (State of Mind) | ~ | ✓ (tags) | ~ | ✗ | ✓ |
| journal/behavior tags | ✓ | ✓ (journal) | ✗ | ✗ | ✓ (tags) | ✗ | ✗ | ✓ |
| cycle phase | ✓ opt-in | ✓ | ✓ (cycle tracking) | ✓ | ✓ | ✓ | ✓ | ✓ |
| baselines mean/sd/n | ✓ | ~ (baseline in payloads) | ✗ (adapter computes) | ~ | ~ | ✗ | ~ | ✗ |
| vo2max | ✓ estimate | ✗ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| spo2 / skin temp | ✗ (unvalidated) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |

Schema-design conclusions (these DID change the design):

1. **No single field is universal except RHR and sleep duration** → every leaf
   stays nullable, `missing_fields` is required, and no task category may *require*
   recovery_score (readiness bucket can be adapter-derived from HRV-vs-baseline +
   RHR-vs-baseline when the provider has no composite score — that derivation rule
   belongs in the adapter spec, not the model).
2. **HRV method mismatch is real** (Apple = SDNN, most others = RMSSD) → added
   `provenance.hrv_method: rmssd|sdnn|unknown` so the model never compares an SDNN
   value against an RMSSD baseline. Adapters must never mix methods in one context.
3. **Strain scales differ** (WHOOP-style 0–21 vs Garmin load vs Fitbit AZM) →
   `provenance.strain_scale` already covered this; rule: adapters either map to
   0–21 honestly or send null + provider value in provider_metadata. Never rescale
   silently.
4. **Baselines are an adapter responsibility**: most providers give raw dailies;
   the adapter computes mean/sd/n windows. Schema unchanged (stats shape works).
5. **Provider masks for training data** (used in data_generation_plan §4/§5):
   `wearable_full` (Atria/WHOOP-like), `ring_no_strain` (Oura-like),
   `platform_aggregate` (Apple-Health-like: no recovery, SDNN, has steps),
   `watch_load_native` (Garmin-like), `tracker_azm` (Fitbit-like),
   `manual_only` (duration + subjective + workouts only).

## 7. Compact-context budget

MVP context serializes to ~600–900 tokens; V1 ~1.2–1.8k; V2 capped ~2.5k by
truncation rules (recent_workouts ≤7, journal_entries ≤7 days, habit_insights ≤3).
Keys are snake_case, stable across versions; adapters must emit `null`, never omit
required keys, so `missing_fields` stays truthful.
