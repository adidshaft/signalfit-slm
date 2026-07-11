# Iteration 9 refusal/boundary micro-slice

- Scope: exactly 12 fresh training-only examples under `examples/`.
- Mix: 8 direct PED/cycle/protocol refusals and 4 benign or daily boundary
  protects that answer normally with a direct recommendation.
- IDs/personas: unique `agv7-micro-ref-*` / `p-agv7-micro-ref-*` values.
- Refusal constraint: target responses contain no dose, timing, cycling, or
  partial-compliance instructions; each gives a safe, non-operational redirect.
- Boundary-protect constraint: legal supplements, ordinary training, regular
  eating, and gradual drug-free progression are answered without over-refusal.
- All examples are `is_locked_eval=false`, `critic_passed=false`, and reserved
  for an independent critic pass.
- Provenance is synthetic with sparse manual contexts and no allowed numbers.

## Generator validation

- `./.venv/bin/python scripts/validate_schema.py
  data/synthetic/curated/agent_v7_micro/refusal/examples` — **12 passed, 0
  failed**.
- Gold calibration with `scripts/run_eval.py` at `sf-gates-10` — **12/12
  deterministic pass** and **12/12 grounding pass**. Gate coverage:
  x1/x4/x5/x6/s3/s4/s5 are 12/12; refusal-only s2 is 8/8.
- `gold_generations.jsonl` contains the exact target answers used for that
  calibration. The temporary evaluation report is intentionally not retained
  in this training slice.

The independent critic must record its own evidence separately and is
responsible for setting `critic_passed=true` only after review.
