# Contracts — what was fixed in place before any training

Everything in this file was written **before** the first fine-tune. The data
must *demonstrate* these contracts and the eval must *measure* them; written
afterwards, they would just describe whatever the model happened to do.

## Schemas

| Contract | File | What it pins |
|---|---|---|
| `sf-context-1` | `schemas/assistant_context.schema.json` | The model's entire world: what a context JSON may contain. Provider-agnostic (WHOOP/Garmin/Oura/manual all map in), every field nullable, `data_quality.missing_fields` says what's absent, `provenance.source_confidence` says what to hedge on. |
| `sf-train-1` | `schemas/training_example.schema.json` | A full training example: context + `task_category` + `case_type` + `difficulty` + `target_response` (gold text, `expected_action`, `required_behaviors`, `forbidden_behaviors`) + `labels` (persona, provider mask, `is_locked_eval`) + `generation` provenance. |
| `sf-chat-1` + `sft-sys-1` | `scripts/prepare_dataset.py` | The exact chat wire format: pinned system prompt (verbatim, versioned), user turn = `CONTEXT:\n<compact sorted JSON>\n\nQUESTION: <q>`, assistant turn = gold text. Any change bumps the format id. |

**Rule:** change a schema → bump its version → everything downstream declares
which version it used. Stable contracts are what make five scripts and dozens
of agents composable.

## The `allowed_numbers` grounding contract

The single most important design idea, borrowed from the Atria reference app's
fabrication check and generalized: **every number the model may say is
enumerated in the context** as `{value, unit, label}` triples (label = dotted
path like `trends.window_7d.avg_strain`). Consequences:

- hallucinated numbers are *mechanically detectable* (regex + ±1.0 tolerance),
- derived values (deltas, "76 minutes under average") are only sayable if
  someone put them in the contract — which is itself a training signal,
- the same check runs at data-entry time (`validate_schema.py`) and at eval
  time (`run_eval.py` x1 gate), so bad examples never get in and bad answers
  never pass.

## Behavior contracts

| Document | Role |
|---|---|
| `docs/safety_policy.md` | When to refuse (PED dosing, crash diets, medical dosing), when to triage (red-flag symptoms; which care level), when to hedge (estimate-grade fields). Safety precedence: flags override task category. |
| `docs/eval_rubrics.md` (`rubric-v0.1`) | Binary pass/fail judge criteria: X1–X7 cross-cutting (grounding truthfulness, hedging, personal-vs-population, follow-up budget, brands, shape, safety precedence) + 3–4 criteria per task category (e.g. D1 "explicit recommendation level", T4 "no metric-based reassurance", I1 "names the actual missing field"). Pinned per eval run; any criterion change bumps the rubric version. |
| `docs/eval_plan.md` | What is measured and the release gates (grounding ≥98%, triage recall 100%, false-refusal ≤3%, judge protocol: temperature-0 equivalent, judged twice, disagreement → human queue). |
| `docs/persona_library.md` | Persona definitions so train/valid can be split **by persona** — validation measures generalization, not memory. |
| `docs/data_generation_plan.md` | Target distribution across 10 task categories × case types × provider masks × difficulty. |
| `docs/finetuning_format.md` | The `sf-chat-1` spec in prose. |
| `docs/product_brief.md`, `docs/schema_design.md` | Framing and schema rationale. |

## The Atria reference

`~/projects/atria` is a **read-only** reference app: the source of the
fabrication-check idea, the export schema used for the real-data test, and the
statistically-gated habit-insight design (Welch p<0.10) that the schema
adopted. It is never modified, and real exports from it live only in
`data/real_world/` (see [data-factory.md](data-factory.md)).

## Anti-overcaution, contractually

The safety slice of every data round is required to include **benign
lookalikes** (sore chest muscles, not cardiac chest pain) labeled *answer
normally*, and the eval reports safety recall and false-refusal **together** —
you cannot game one by tanking the other. (The `agent_v3_relational` round
omitted its lookalikes — recorded as a known gap in
[iterations.md](iterations.md).)
