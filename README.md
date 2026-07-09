# SignalFit-SLM

## Project Stages

| Stage | No. | Description | Status |
|---|---:|---|---|
| Foundation | 1 | Product framing, universal wearable context schema, safety policy, and eval rubric. | ✅ Done |
| Seed Pipeline | 2 | Synthetic seed examples, validation scripts, dataset prep, and split workflow. | ✅ Done |
| ft_v1 | 3 | First MLX LoRA fine-tune and locked-set smoke evaluation. | ✅ Done |
| ft_v2 Safety | 4 | Targeted safety supplement, triage/refusal gates, retrain, and improved safety behavior. | ✅ Done |
| Frozen Eval | 5 | Frozen `eval/v1` suite, judge workflow, regression gate, and `sf-gates-4` comparative arithmetic. | ✅ Done |
| ft_v3 Relational | 6 | Relational/safety data round, retrain, and full-suite eval; blocked by regression, not promoted. | ⚠️ Evaluated |
| Claim Discipline | 7 | Next loop for unsupported qualitative claims, stronger rubric training, and future baseline candidate. | 🔜 Future |

SignalFit-SLM is a small language model project for grounded fitness coaching.
It takes a normalized wearable-health context plus a user question, then returns
an answer that stays inside the supplied data and safety policy.

## Description

This project explores how to build a trustworthy assistant for wearable fitness
data. The model is trained and evaluated on structured context objects rather
than raw chat logs, which makes it easier to keep answers grounded, auditable,
and provider-agnostic.

## Highlights

- universal context schema for wearable and fitness data
- synthetic generation pipeline with critique and validation steps
- safety policy focused on refusal, escalation, and missing-data handling
- evaluation plan for grounding and behavioral quality
- MLX and Unsloth training organization

The project is designed to work across providers such as WHOOP, Atria, Apple
Health, Garmin, Oura, Fitbit, Ultrahuman, and manual logs, as long as the data
is converted into the shared assistant-context schema.

## What This Repo Is

This repository contains the full workflow for the project:

- schema design for the universal wearable context
- synthetic data generation and critique prompts
- curated training and evaluation datasets
- safety policy and evaluation plan
- training configs for MLX and Unsloth
- lightweight scripts for validation, dataset prep, and splitting

## What This Repo Is Not

- It is not a storage location for real user health exports.
- It is not provider-specific software.
- It is not a medical device or diagnostic system.

## Current Focus

The current emphasis is on:

- grounded answers that only use numbers present in the provided context
- safety-aware coaching that refuses or escalates when needed
- dataset quality over raw scale
- reproducible training and evaluation

## Why This Exists

Most fitness assistants are tied to one vendor, one device, or one app. This
project tries to separate the intelligence layer from the data source so the
same assistant can reason over different providers as long as the context is
normalized first.

## Repository Layout

| Path | Purpose |
|---|---|
| `docs/product_brief.md` | Project framing and goals |
| `docs/schema_design.md` | Canonical context schema and provider mapping notes |
| `docs/safety_policy.md` | Safety rules, refusal boundaries, and red-flag handling |
| `docs/data_generation_plan.md` | Synthetic data strategy and collection plan |
| `docs/eval_plan.md` | Evaluation design and quality gates |
| `schemas/` | JSON Schemas for assistant context and training examples |
| `prompts/` | Teacher-model prompts for generation, critique, discovery, and eval case creation |
| `data/synthetic/` | Synthetic examples, split into `raw/` and `curated/` |
| `data/eval/` | Locked evaluation data |
| `data/real_world/` | Local-only placeholder for private exports and adapter testing |
| `training/` | Training configs and run organization |
| `notebooks/` | Exploratory analysis and experiments |
| `scripts/` | Validation, dataset prep, and splitting helpers |
| `models/` | Model notes and artifact references |

## Data Handling

Real user exports are intentionally kept out of the repository.

- `data/real_world/` is a placeholder only.
- Synthetic data belongs in `data/synthetic/`.
- Eval data belongs in `data/eval/`.
- Large artifacts and generated files are ignored through `.gitignore`.

If you are adapting this project to your own data, start by mapping your provider
exports into `schemas/assistant_context.schema.json`, then validate that mapping
before using it for training or eval.

## Validation Example

I tested the model against actual WHOOP data pulled from ATRIA
(`atria.zookfit.in`) and confirmed that the LLM could answer with timestamps,
sleep, recovery, and training context intact.

![ATRIA WHOOP validation screenshot](/var/folders/l9/3shhw7rn0nq9g4f07h5rs50m0000gn/T/codex-clipboard-b632cd1d-7b04-46cf-b9a6-6a3cbc39c7aa.png)

## How To Use It

Typical workflow:

1. Convert provider-specific data into the assistant-context schema.
2. Validate the result with `scripts/validate_schema.py`.
3. Prepare or split datasets with the helper scripts in `scripts/`.
4. Train using the configs under `training/`.
5. Evaluate on the locked eval set under `data/eval/`.

The model itself is context-bound: it does not have live access to your account
or wearables, so each answer depends on the input context you provide.

## Safety Position

The assistant is meant to support fitness decisions, not replace medical care.
It should:

- refuse unsafe requests
- avoid diagnosis
- point out missing context when the data is incomplete
- recommend real-world care for urgent symptoms or concerning patterns

See `docs/safety_policy.md` for the formal policy.

## Status

The repository currently documents a working grounded-coaching pipeline with
schema design, synthetic data tooling, evaluation scaffolding, and model run
notes. It is meant to be shared, inspected, and extended.

## Contact

Maintainer: adidshaft <adidshaft@gmail.com>
