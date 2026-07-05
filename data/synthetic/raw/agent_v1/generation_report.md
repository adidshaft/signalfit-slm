# Agent-workflow generation report — agen-v1 (phase 1: 300 examples)

Method: no paid APIs. Deterministic contexts from `scripts/make_context_specs.py`
(seed 301); a **Generator subagent** (owner-delegated agent, this session) writes
question/answer/labels per chunk of 30; the deterministic **validator**
(`scripts/validate_schema.py`: JSON-Schema + grounding gate) must pass 30/30;
a **Critic subagent** then reviews each chunk against `docs/eval_rubrics.md`
and the phase-1 rules (brands, ≤1 follow-up, anti-conservatism, safety
precedence), fixing minor issues or rejecting. Only clean examples move to
`data/synthetic/curated/agent_v1/`.

Category plan: explain_metric 40 · daily_training_decision 45 ·
recovery_explanation 40 · sleep_coaching 35 · plan_adjustment 35 ·
goal_coaching 30 · habit_pattern_analysis 25 · insufficient_data_followup 20 ·
safety_triage 20 · refusal_or_redirect 10. Locked eval: 30 (~10%/category,
disjoint eval personas).

## Chunk log

| Chunk | Generated | Passed validator | Critic: fixed | Rejected | Notes |
|---|---|---|---|---|---|

## Failure modes observed

(running list)

## Final category counts

(filled at completion)
