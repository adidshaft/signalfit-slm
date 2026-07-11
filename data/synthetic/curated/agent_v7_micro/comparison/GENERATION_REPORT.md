# Iteration 9 comparison micro-slice

Generated 2026-07-13 as a training-only, bounded repair slice. This directory
contains exactly 16 fresh examples (`agv7-micro-comp-001` through
`agv7-micro-comp-016`) with distinct `p-agv7-micro-comp-*` personas.

Coverage is limited to the observed comparison/grounding residue:

- HRV, resting-heart-rate, and recovery references with correct above, below,
  near-equality, and mixed directions;
- confusable contexts containing several current and reference values, with
  every claim bound to its matching metric;
- sleep-duration comparisons stated in recorded minutes, without invented
  deficits, deltas, targets, or recommendation numbers.

All examples are training-only (`is_locked_eval: false`) and intentionally
retain `critic_passed: false` for independent review. No evaluation cases,
answers, wording, personas, or values were copied into this slice.

Generation-time checks:

- `scripts/validate_schema.py`: **16 passed, 0 failed**.
- Gold calibration with `scripts/run_eval.py` at `sf-gates-10`: deterministic
  **16/16** and grounding **16/16**.
- Applicable gate results: x1, x4, x5, x6, s3, s4, and s5 all **16/16**.

The temporary gold JSONL and evaluation report were kept outside the curated
directory. Independent critic review remains deliberately outstanding.
