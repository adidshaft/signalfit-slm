# agv7 Qwen3 repair — protect set generation report

Generated 2026-07-12 under the training-only repair contract
`agv7-qwen3-repair-1`. This directory contains 24 fresh examples:

- `agv7-protect-000` through `agv7-protect-011`: 12 unambiguous safety
  positives — 7 direct refusals (PED or dangerous-cut requests) and 5
  eating-disorder triage responses.
- `agv7-protect-012` through `agv7-protect-023`: 12 benign lookalikes — 6
  daily-training decisions and 6 ordinary food/supplement/refusal lookalikes.

All 24 examples use distinct `p-agv7-protect-*` personas, set
`is_locked_eval: false`, and deliberately retain `critic_passed: false` for
independent review. The IDs and personas have no overlap with `eval/v1`.

Validation results:

- `scripts/validate_schema.py`: **24 passed, 0 failed**.
- Gold calibration with `scripts/run_eval.py` at `sf-gates-10`: deterministic
  **24/24**, grounding **24/24**. Every applicable gate passed: x1/x4/x5/x6,
  s3/s4/s5 all 24/24; s2 refusal 7/7; s1 triage 5/5.

The temporary gold generations and evaluator output were removed after the
successful run so the curated directory remains directly validator-safe; the
results above are the retained handoff record.
