# SignalFit-SLM — Product Brief (v0.1 draft)

Status: analysis-only draft, generated 2026-07-05. Not yet copied into the repo.

## What it is

SignalFit-SLM is a small language model that acts as a personal fitness assistant. It
consumes a **normalized wearable-fitness context** (the SignalFit schema) plus a user
question, and produces grounded, safe, personalized coaching answers.

It is **provider-agnostic by design**:

```
Any provider (WHOOP, Apple Health, Garmin, Oura, Fitbit, Ultrahuman, manual logs, Atria, custom apps)
        │  provider-specific adapter
        ▼
SignalFit universal context schema  (canonical JSON)
        │
        ▼
SignalFit-SLM  →  grounded coaching answer
```

Atria is the **first reference adapter only**. Nothing in the model, schema, or
training data may assume WHOOP hardware or Atria branding. Provider-specific detail
lives exclusively in an optional `provenance.provider_metadata` object.

## Why a small model

- Runs locally / on-device → privacy story matches source apps like Atria
  (whose local AI coach mode explicitly promises "no data leaves this iPhone").
- The task is narrow: interpret a compact numeric context, answer one question,
  respect safety policy. A 1–8B model fine-tuned on schema-shaped data is the target.
- Compact canonical schema keeps context under ~2–3k tokens even in the V2 shape.

## Core product principles (derived from the Atria reference implementation)

1. **Answer only from DATA.** Atria's coach system prompt is literally:
   *"Answer ONLY from DATA. If a value is not in DATA, say you don't have it — never
   estimate, never use population numbers as if personal."* SignalFit-SLM adopts this
   as a training objective, enforced by an `allowed_numbers` fabrication-check list
   in the schema (generalizing Atria's `serializedNumbers` + `fabricationFlags`).
2. **Honest confidence.** Every derived metric carries a confidence/evidence label
   (Atria does this pervasively: `recoveryConfidence`, `SleepStageEvidence`,
   `caloriesConfidence`, ACWR `confidence: "learning"`). The model must degrade its
   language when confidence is low ("estimated", "still learning your baseline").
3. **Missing data is first-class.** The schema carries `missing_fields`; the model
   is trained to name what's missing and ask for it rather than guess.
4. **Safety before coaching.** A safety-triage layer (see safety_policy.md) always
   outranks task completion.
5. **Not a medical device.** The model never diagnoses, never claims clinical
   accuracy, and refers out on red flags.

## What the model answers (task categories, detailed in schema_design.md §5)

explain_metric · daily_training_decision · recovery_explanation · sleep_coaching ·
plan_adjustment · goal_coaching · habit_pattern_analysis · safety_triage ·
insufficient_data_followup · refusal_or_redirect

## Deliverable roadmap

| Phase | Artifact |
|---|---|
| Now | Universal schema (MVP/V1/V2), safety policy, data-generation + eval plans |
| Next | Synthetic dataset v1 (~3.5k examples) in `training_example` format, locked eval set |
| Then | Fine-tune small model (MLX / Unsloth dirs already scaffolded), eval harness |
| Later | Atria adapter (Atria rollups → SignalFit context), other provider adapters |

## Non-goals (v1)

- No nutrition planning beyond context awareness; no meal plans.
- No medical interpretation of SpO2/skin-temp/ECG-like signals.
- No multi-user / social features.
- No write path back to providers.
