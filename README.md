# SignalFit-SLM

A small language model that acts as a personal fitness assistant. It consumes a
**normalized, provider-agnostic wearable-fitness context** plus a user question and
produces grounded, safe, personalized coaching answers.

```
Any provider (WHOOP, Apple Health, Garmin, Oura, Fitbit, Ultrahuman, manual logs, Atria, custom apps)
        │  provider-specific adapter
        ▼
SignalFit universal context schema   (schemas/assistant_context.schema.json)
        │
        ▼
SignalFit-SLM  →  grounded coaching answer
```

SignalFit-SLM is **not** WHOOP-specific and **not** Atria-specific. Atria
(`~/projects/atria`, treated strictly as read-only reference material) is the first
reference data provider only; device/app-specific detail lives exclusively in the
optional `provenance.provider_metadata` object of the schema.

## Core principles

1. **Answer only from DATA** — every number the model may state is enumerated in the
   context's `allowed_numbers` list (fabrication guard).
2. **Honest confidence** — derived metrics carry confidence/evidence grades; the
   model hedges on estimate-grade data.
3. **Missing data is first-class** — `missing_fields` is required; the model names
   gaps instead of guessing.
4. **Safety before coaching** — see `docs/safety_policy.md`.
5. **Not a medical device** — never diagnoses, refers out on red flags.

## Repository layout

| Path | Contents |
|---|---|
| `docs/product_brief.md` | Product framing, principles, roadmap |
| `docs/schema_design.md` | Atria field inventory (verified), canonical schema, provider coverage matrix, MVP/V1/V2 tiers, task categories |
| `docs/safety_policy.md` | Safety policy v1 (red flags, refusal rules, never-claim list) |
| `docs/data_generation_plan.md` | Synthetic data plan (3.5k train + 500 locked eval) |
| `docs/eval_plan.md` | Eval metrics, gates, harness shape |
| `schemas/` | Canonical JSON Schemas: assistant context (`sf-context-1`) and training example (`sf-train-1`) |
| `prompts/` | Teacher-model prompts: generation, critic, eval-case generation, schema discovery |
| `data/synthetic/` | Generated examples (`raw/` → critic → `curated/`) |
| `data/eval/` | Locked eval sets (checksummed, never trained on) |
| `data/real_world/` | Local-only real exports for adapter testing — **gitignored by design** |
| `scripts/` | Dataset pipeline (validate/prepare/split) — not yet implemented |
| `training/` | Fine-tuning configs (MLX / Unsloth) — not yet implemented |
| `models/` | Model artifacts and run notes — see `models/README.md` |

## Status (2026-07-05)

Design phase. Schema v0.1 and all planning docs drafted and iterating; no data
generated and no model trained yet. Next: worked end-to-end examples, then the
dataset pipeline scripts.
