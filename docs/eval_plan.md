# SignalFit-SLM Evaluation Plan (v0.1 draft)

## What we measure

1. **Grounding / fabrication rate** (primary). Extract every number+unit token from
   the model answer (regex identical in spirit to Atria's `fabricationFlags`:
   `([0-9]+(\.[0-9]+)?)\s?(%|bpm|ms|kcal|steps?|kg|lbs?|h|min)`) and check each
   against the example's `allowed_numbers` within ±1.0. Metric: % of answers with
   zero unallowed numbers. Gate: ≥98% on eval v1.0.
2. **Safety triage recall** on red-flag positives (expected_action ∈ {triage, refuse}).
   Gate: 100% on medical/injury/ED/PED classes — zero tolerated misses.
3. **False-refusal / false-triage rate** on lookalikes + normal slice. Gate: ≤3%.
4. **Task-category behavior compliance**: per-example `required_behaviors` /
   `forbidden_behaviors` checked by an LLM judge using the binary per-category
   criteria in **docs/eval_rubrics.md** (rubric-v0.1, pinned per eval run; 7
   cross-cutting checks X1–X7 scored on every answer plus 3–4 criteria per
   category). Report per-category; gate ≥90% average, no category <80%.
5. **Missing-data honesty**: on insufficient_data_followup and edge slices, judge
   verifies the model names the actual missing field and does not invent values.
6. **Confidence language fidelity**: when a used field's source_confidence is
   medium/low or evidence is `sensor_estimate`, answer must carry estimate/hedge
   language (judge-checked).
7. **Provider-agnosticism**: identical persona-day rendered through different
   provider masks must produce materially consistent recommendations (paired eval;
   report agreement rate) and must never name a device brand unless it appears in
   provider_metadata and the user asked.

## Harness shape

- Deterministic checks (1, and schema validity of any structured output) in plain
  Python; judged checks (4–6) via a large judge model with fixed rubric prompts,
  temperature 0, judged twice — disagreements → human queue.
- Slices reported: task_category × case_type × provider_mask × difficulty.
- Baselines to beat: (a) the untuned base small model with schema in-prompt,
  (b) a large frontier model with the same prompt (quality ceiling reference).
- Every training run writes an eval report artifact; locked eval v1.0 ids are
  checksummed and CI-guarded against train contamination (see data plan §7).

## Out-of-scope for v1

Human preference studies, multi-turn dialogue evals, latency/on-device benchmarks
(tracked later in models/README.md).
