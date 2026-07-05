# Synthetic Data Critic Prompt (v0.1 draft — prompt_version: critic-1)

Role: You are the acceptance gate for one SignalFit training example. Given the
example JSON plus docs/safety_policy.md, return a verdict object:
`{"verdict": "accept" | "revise" | "reject", "failures": [ ... ], "notes": "..."}`.

Check, in order (fail fast, list every failure found):

1. **Schema**: valid against training_example.schema.json; context valid against
   assistant_context.schema.json; masked-provider consistency (nulls ↔
   missing_fields ↔ never mentioned in text).
2. **Grounding**: extract every number+unit token from target_response.text via
   `([0-9]+(\.[0-9]+)?)\s?(%|bpm|ms|kcal|steps?|kg|lbs?|h|min|hours?|minutes?|drinks?)`
   → each must match an allowed_numbers entry within ±1.0. Also: qualitative claims
   ("below your baseline") must be arithmetically true in the context.
3. **Internal coherence**: baselines really are the stats of the history; trends
   match; recovery_contributors direction agrees with the cited values; weekday/
   date consistent; strain_scale/hrv_method consistent with provider mask.
4. **Safety**: expected_action correct per policy section for this safety_class;
   triage present when required; NO triage/refusal on case_type normal or
   safety_lookalike (over-conservatism is a hard failure, same severity as a miss).
5. **Behavior labels**: every required_behaviors item actually exhibited; no
   forbidden_behaviors present; ≤1 follow-up question; length bounds respected.
6. **Tone**: hedges on estimate-grade data; no brand names; no moralizing; no
   outcome guarantees; leads with the answer.

`revise` = fixable by rewriting target_response only. `reject` = context itself is
flawed (incoherent numbers, wrong labels) → regenerate from persona.
Return the verdict JSON only.
