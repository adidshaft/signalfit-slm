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
| 01 | 30 | 30/30 (first run) | 0 | 0 | clean; mild template repetition flagged |
| 02 | 30 | 30/30 (first run) | 2 | 0 (1 initially rejected, rewritten by orchestrator) | 000039 habit-attribution rewrite; 000046 duplicated opening reworded |
| 03 | 30 | 30/30 (first run) | 1 | 0 | fainting triage care-level firmed to immediate; refusal length trimmed by generator |
| 04 | 30 | 30/30 (first run) | 5 | 0 | 3x breathing-difficulty triage upgraded to immediate care; 1 habit caveat added; 1 causal phrasing softened |
| 06 | 30 | 30/30 (first run) | 1 | 0 | agen-2 prompt: safety/habit rules held; one temporal-reference slip fixed |

Curated so far: **150 / 300** (chunk 05 pending critic).

## Failure modes observed

1. **Habit-pattern over-assertion** (1 reject → rewritten): generator asserted a
   habit→metric pattern with no gated insight/tagged days in context; correct
   form is "numbers look good, attribution not establishable, here's what to
   log" (rubric H1/H3). Generator prompts for later chunks should call this out.
2. **Answer-template repetition** (mild, both chunks): recurring openings and
   the "X vs your 30-day average of Y" skeleton; one file reworded. Later
   chunks get a stronger variety instruction.
3. **Triage care-level borderline** (accepted, watch): two fainting cases said
   "see a clinician today" where policy §8 lists fainting as immediate-care;
   answers included escalation triggers so they passed, but later chunks
   should prefer immediate care for syncope.
4. **Category drift in question phrasing** (benign): a goal_coaching question
   worded like recovery_explanation; answers still met their own rubric.

## Final category counts

(filled at completion)
