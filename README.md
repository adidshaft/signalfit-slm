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
| `docs/using_and_finetuning.md` | **Guide for others**: run the model, feed it your data, fine-tune on your own examples |
| `schemas/` | Canonical JSON Schemas: assistant context (`sf-context-1`) and training example (`sf-train-1`) |
| `prompts/` | Teacher-model prompts: generation, critic, eval-case generation, schema discovery |
| `data/synthetic/` | Generated examples (`raw/` → critic → `curated/`) |
| `data/eval/` | Locked eval sets (checksummed, never trained on) |
| `data/real_world/` | Local-only real exports for adapter testing — **gitignored by design** |
| `scripts/` | Dataset pipeline: validate / prepare / split / generate / eval / ask |
| `training/` | MLX LoRA configs and runbook |
| `models/` | Model artifacts and run notes — see `models/README.md` |

## Trying and testing the model

The current model is **ft_v2**: Qwen2.5-1.5B-Instruct + LoRA adapters trained on
400 curated examples (see `models/README.md` for the run log). One-time setup:

```bash
python3 -m venv .venv
.venv/bin/pip install jsonschema anthropic 'mlx-lm==0.31.3' 'transformers<5'
# note: mlx-lm on Python 3.14 may need a one-line patch — see
# docs/process_guide.md "Dependency reality check"
```

### Ask it a question

The model answers ONLY from a context JSON (`sf-context-1`) — it has no memory
or live data. Use any curated example as the context:

```bash
# random context from the dataset
.venv/bin/python scripts/ask.py --random "should I train hard today?"

# specific context (bare context or full training-example file)
.venv/bin/python scripts/ask.py data/synthetic/curated/agent_v1/agen-v1-000138.json \
  "woke up feeling meh, worth doing my long ride?"
```

`ask.py` prints the answer and warns if the model cites any number outside the
context's `allowed_numbers` (the fabrication check).

### Run the full evaluation

```bash
# 1. generate answers for the locked eval split (never trained on)
.venv/bin/python scripts/generate_answers.py data/ft_v2/eval.jsonl \
  --adapter models/adapters/ft_v2_qwen2.5-1.5b -o /tmp/gens.jsonl

# 2. score against the deterministic gates (grounding, follow-up budget,
#    brands, length, no-coaching-in-triage, no-protocol-in-refusal)
.venv/bin/python scripts/run_eval.py \
  --examples data/synthetic/curated/agent_v1 data/synthetic/curated/agent_v2_safety data/synthetic/curated/worked_examples \
  --generations /tmp/gens.jsonl --out-dir /tmp/eval_report
```

Expected (ft_v2 baseline on the current gates, incl. field-binding): deterministic
gates 33/40, grounding 39/40, triage 6/6, zero protocol leakage. `judge_bundle.jsonl` in the report dir holds
per-example rubric prompts for an optional LLM-judge pass.

### Validate the dataset

```bash
.venv/bin/python scripts/validate_schema.py data/synthetic/curated/agent_v1 \
  data/synthetic/curated/agent_v2_safety data/synthetic/curated/worked_examples
```

### Serve it as an API

```bash
.venv/bin/python -m mlx_lm server --model Qwen/Qwen2.5-1.5B-Instruct \
  --adapter-path models/adapters/ft_v2_qwen2.5-1.5b --port 8080
# then POST OpenAI-style chat-completions to localhost:8080
```

### Retrain from scratch

The whole pipeline is reproducible: `docs/process_guide.md` documents every
step (data generation → validation → critique → JSONL → split → LoRA → eval)
with the exact commands.

## Status (2026-07-06)

Phase 2a complete: 400-example curated dataset (300 general + 100 safety
supplement), ft_v2 fine-tune with safety behaviors verified (triage 6/6, zero
refusal protocol leakage), deterministic eval gates in place. Next: quality
polish round, dataset scale-up, or iOS quantization (fuse → 4-bit → MLX Swift).
