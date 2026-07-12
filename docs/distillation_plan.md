# Distillation-to-scale plan (the $0 path to a stable fine-tuned model)

## Why this exists

Iterations 15A→18A converged on one diagnosis: the binding constraint is no
longer any single fixable defect — it is **capability/stability variance at
1.7B with ~1,138 curated rows**. Every retrain of the same recipe flips 2–3
protect cases at random (16A→17A evidence). Micro-rounds of 18–30 examples
cannot fix variance; only more high-quality training signal can. A stable
distilled student typically needs **5–10k gate-clean rows**, not ~1k.

The project rule is "no paid APIs for data generation." The existing
`scripts/generate_teacher_batch.py` uses the Anthropic Batch API and is
therefore **out of scope**. This plan uses only free local compute.

## The mechanism we already have

`agent_v1 … agent_v9` were already distillation: a capable generator writes
gate-clean answers over deterministic contexts, an independent critic filters,
the student trains on the survivors. Everything is in place except **scale and
a non-manual generator**:

- `scripts/make_context_specs.py` — builds unlimited deterministic contexts
  (coherent numbers, complete `allowed_numbers`) with **no API**. This is the
  context source; it can emit thousands of specs.
- `scripts/run_eval.py::check` (sf-gates-12) — the grounding/safety filter that
  every teacher answer must pass before entering the dataset.
- `scripts/prepare_dataset.py` / `split_dataset.py` — dataset assembly.
- `scripts/answer_with_check.py` — the wrapper the student is served behind.

## What to add: a local teacher

Run a larger open model **locally via mlx** as the answer generator — free,
offline, and it fits alongside training on the 24 GB Mac:

- **Candidate teacher:** `mlx-community/Qwen3-8B-4bit` (~4.5 GB) or
  `Qwen3-14B-4bit` (~8 GB) if memory allows. Apache-2.0, consistent with the
  base-selection rule. A 4-bit 8B teacher is materially stronger than the
  1.7B student on exactly the arithmetic-binding and refusal-discipline cases
  that churn (ev1x-core2 sleep-debt ratios, protocol-in-refusal).
- **Generation:** for each context spec, prompt the teacher with the frozen
  serving system prompt + CONTEXT + QUESTION, sample an answer.
- **Gate filter (non-negotiable):** run every teacher answer through
  sf-gates-12 `check`. Only gate-clean answers enter the pool. This is the
  quality floor that makes teacher noise harmless — a wrong teacher answer is
  simply discarded, never trained on.
- **Independent critic pass:** sample-audit the surviving pool with a critic
  agent (as in agv9) for coherence/binding the gates can't see; quarantine
  FIX/REJECT.
- **Contamination guard:** `freeze_eval.py` already blocks train/valid overlap
  with the frozen suite; teacher contexts use a disjoint persona namespace.

## Target dataset shape

- **Volume:** 5,000–8,000 gate-clean rows, category-balanced to the eval
  suite's mix (over-weight the churn-prone categories: plan_adjustment,
  recovery_explanation, sleep_coaching, refusal_or_redirect).
- **Provenance:** each row stamped with teacher model id, sampling params,
  gate version, and critic verdict — same manifest discipline as the curated
  rounds.
- **Locked eval untouched:** eval/v1 stays frozen; no teacher row is locked
  eval.

## Training and acceptance

- Train the student (Qwen3-1.7B, current best recipe) on the scaled dataset.
- **Multi-seed selection** (the iteration-18 fallback, promoted to standard):
  train 3–5 seeds, run the deterministic prefilter on each, promote the first
  that clears all 46 protects. Scale should shrink protect variance; selection
  removes what remains.
- The frozen suite + owner-review packet remain the only promotion gate. A
  distilled candidate earns promotion exactly like any other — no shortcut.

## Ship path (unchanged, after any promotion)

fuse LoRA → 4-bit quantize → re-run the full 200-case suite on the
**quantized** system (quantization can shift behavior; it must re-clear the
gates) → HF upload.

## Sequencing

1. Finish iteration 18A (serving-layer repair of ft_v9) — may promote without
   any of this.
2. If 18A stalls on the one capability case, run multi-seed selection on the
   existing dataset first (cheapest capability lever).
3. In parallel and regardless: download a local teacher, build the
   local-teacher generation script, and produce the first 1–2k gate-clean rows
   as a pilot — measure the gate pass-rate of raw teacher output to size the
   full run.
4. Scale to 5–8k, retrain, multi-seed select, review, promote, ship.

Step 3 is the first genuinely new capability investment since the base-model
selection; steps 1–2 are cheaper and come first.
