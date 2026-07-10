# agv7 daily-training-decision repair slice

Generated on 2026-07-11 for the Qwen3 repair loop. This is training-only data;
it does not modify or extend the locked evaluation suite.

- 48 fresh `agv7-daily-*` examples and `p-agv7-daily-*` personas
- 24 normal decisions, 12 recovery-null/provider-missing decisions, and 12
  safety-precedence triage decisions
- All examples have `is_locked_eval: false` and `critic_passed: false`
- No exact evaluation question or persona collisions were found in the local
  isolation audit

Verification completed:

```text
.venv/bin/python scripts/validate_schema.py \
  data/synthetic/curated/agent_v7_qwen3_repair/daily
# 48 passed, 0 failed

.venv/bin/python scripts/run_eval.py \
  --examples data/synthetic/curated/agent_v7_qwen3_repair/daily \
  --generations data/synthetic/curated/agent_v7_qwen3_repair/daily/gold_generations.jsonl \
  --out-dir /tmp/agv7_daily_gold_eval
# sf-gates-10 gold calibration: 48/48 deterministic pass
# x1/x4/x5/x6/s1/s3/s4/s5: all applicable checks pass
```

`generate_daily_slice.py` is the compact, target-only provenance generator and
`gold_generations.jsonl` contains the matching target answers used for the
calibration above.
