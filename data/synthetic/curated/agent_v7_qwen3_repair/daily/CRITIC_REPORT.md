# agv7 daily-training-decision critic report

Independent review completed 2026-07-12 against
`prompts/agv7_qwen3_repair_generation.md`, `docs/eval_rubrics.md`,
`docs/safety_policy.md`, and both training/context schemas.

## Scope and acceptance

- Reviewed all 48 training-only `agv7-daily-*` records: 24 normal decisions,
  12 recovery-composite-unavailable decisions, and 12 safety-precedence cases.
- All records have distinct `agv7-*` ids and `p-agv7-*` personas. Direct
  comparison with `eval/v1/cases` found zero eval id, persona, or exact-question
  collisions.
- All 48 targets lead with a valid decision level, use one to three
  context-traceable reasons, and specify exactly one concrete next action. The
  12 recovery-null cases explicitly state that the composite is unavailable and
  reason from HRV, resting heart rate, and sleep instead.
- The 12 safety cases preserve safety precedence: no workout prescription,
  diagnosis, or wearable reassurance. The dark-urine-plus-weakness case was
  corrected from urgent to **immediate** medical-care language, consistent with
  possible rhabdomyolysis handling in the safety policy.

## Corrections

1. Added explicit medium-confidence framing to each physiology/sleep-based
   daily decision, satisfying X2 rather than presenting medium-confidence
   wearable signals as unqualified facts.
2. Normalized recovery-null targets so the unavailable composite is stated
   independently, then the decision is grounded only in the available signals.
3. Updated the generator provenance and regenerated matching gold answers;
   every accepted record now has `generation.critic_passed: true`.

## Verification

```text
.venv/bin/python scripts/validate_schema.py \
  data/synthetic/curated/agent_v7_qwen3_repair/daily
# 48 passed, 0 failed

.venv/bin/python scripts/run_eval.py \
  --examples data/synthetic/curated/agent_v7_qwen3_repair/daily \
  --generations data/synthetic/curated/agent_v7_qwen3_repair/daily/gold_generations.jsonl \
  --out-dir /tmp/agv7_daily_critic_final
# sf-gates-10: 48/48 deterministic pass
# x1/x4/x5/x6/s1/s3/s4/s5: every applicable check passed
```
