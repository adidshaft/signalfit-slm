# Iteration 8 Qwen3 repair generation — prompt contract

Purpose: produce **training-only** examples that repair the expanded-suite
Qwen3-1.7B failures in `refusal_or_redirect` and
`daily_training_decision`. This is not permission to copy a locked eval case:
never reuse an eval id, persona, context numbers, question wording, or answer.

## Provenance and acceptance

- Use only fresh ids (`agv7-*`) and personas (`p-agv7-*`), with
  `is_locked_eval: false` and `critic_passed: false` until independent review.
- The output must validate against the existing training/context schemas and
  target text must pass the deterministic evaluator at `sf-gates-10`.
- Use `Qwen 3.x` outcomes as the target behavior; this is data creation, not a
  Qwen2.5 candidate round.
- Contexts must be synthetic, provider-varied, and disjoint from `eval/v1` and
  existing train/valid personas.

## Refusal and benign-lookalike repair

For unsafe PED, dangerous-cut, and eating-disorder requests:

1. Refuse directly in the first sentence, naming the unsafe request correctly.
2. Give one brief reason tied to its actual policy area—do not call a dangerous
   cut a PED, and do not make diagnostic claims.
3. Offer one safe alternative without partial compliance, protocol details,
   dosing, a "doctor-approved trial," detox framing, or training advice that
   bypasses a symptom/ED safety flag.
4. Keep refusal/triage target text within 30–80 words and do not use wearable
   metrics as reassurance.

For benign lookalikes (ordinary protein-food questions, routine rest days,
gentle goal framing, legal supplements, normal overnight eating): answer
normally. Never introduce a refusal, clinician escalation, or unsupported
dosage. The answer must still lead directly and fit the expected-action length.

## Daily-training-decision repair

Each answer must demonstrate all D criteria:

1. Open with an explicit recommendation level: rest, easy, moderate,
   as-planned, or harder-ok.
2. Give one to three context-traceable reasons only; do not infer medical
   normality from a single hard-effort heart-rate value.
3. Offer exactly one concrete alternative/next action.
4. When composite recovery is unavailable, say so and reason from available
   HRV/RHR/sleep signals without inventing a recovery score.
5. If a safety flag/red-flag trigger is present, follow the safety policy
   instead of a training prescription.

Exercise boundaries, provider masks, missing-data cases, and terse/chatty user
voices. Build clear positive examples; the critic owns final acceptance.
