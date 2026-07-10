# agv7 Qwen3 refusal repair slice

- Scope: 48 training-only examples in `examples/`; none are locked eval data.
- Mix: 24 direct refusals (8 PED requests, 8 dangerous weight-cut requests,
  8 eating-disorder/compensatory-behavior requests) and 24 benign lookalikes.
- IDs/personas: `agv7-refusal-*` / `agv7-lookalike-*`, with fresh
  `p-agv7-refusal-*` personas. Independent review accepted all records;
  see `CRITIC_REPORT.md`.
- Provenance: synthetic, provider-varied sparse contexts; no target answer
  states a number, so `allowed_numbers` is intentionally empty.
- Prompt contract: `agv7-qwen3-repair-refusal-v1`, derived from
  `prompts/agv7_qwen3_repair_generation.md`.

## Validation evidence

- `./.venv/bin/python scripts/validate_schema.py data/synthetic/curated/agent_v7_qwen3_repair/refusal/examples`
  — **48 passed, 0 failed**.
- Gold generation uses each record's exact target answer. `scripts/run_eval.py`
  at **sf-gates-10** — **48/48 deterministic pass** and **48/48 grounding
  pass**. Gate coverage: x1/x4/x5/x6/s3/s4/s5 are 48/48; refusal-only s2 is
  24/24. The calibration output was intentionally not retained because this
  directory itself must remain a `validate_schema.py`-valid slice (the
  calibration report format is not a training-example schema).

The slice deliberately uses normal `goal_coaching` answers for the lookalikes:
ordinary food, legal supplements, rest days, gentle goals, and overnight eating
are never refused or escalated.
