# agv5 Boundary Generation Contract

Prompt version: `agv5-boundary-1`

Generate only examples assigned to your chunk in
`data/synthetic/curated/agent_v5_boundary/chunk_XX/`. Read Step 7i of
`docs/process_guide.md`, `docs/eval_rubrics.md`, `docs/safety_policy.md`, the
training schemas, and representative curated agv4 examples before writing.
Never copy an immutable eval case, question, context, or answer.

## Global invariants

- Exactly 24 JSON files per chunk, using the assigned consecutive
  `agv5-000000` IDs and fresh `p-agv5-*` personas.
- Use `schema_version: sf-train-1`, prompt version `agv5-boundary-1`,
  `critic_passed: false`, `human_reviewed: false`, and `is_locked_eval: false`.
- Every number+unit in the target response must appear in `allowed_numbers`.
  Qualitative comparisons must be arithmetically true.
- Normal answers are 60–160 words; triage/refusal answers are 30–80 words.
  Lead with the answer, cite 1–3 grounded reasons, and give at most one action.
- Explicitly hedge manual, medium/low-confidence, and estimate-grade data.
- Never invent a recommendation duration, derived number, contributor,
  diagnosis, missing field, pattern, or causal relationship.

## Matched boundary pairs

Chunks 01–03 contain 12 pairs each. Pair members are consecutive IDs and share
one persona ID. Their provider, numeric physiology, baselines, trends, date,
and non-symptom wording must be identical. Flip exactly one semantic symptom
feature plus the labels required to represent it:

- benign member: `case_type: safety_lookalike`, no red-flag safety flag,
  coaching task category, and `expected_action: answer` or
  `answer_with_caveat`;
- red-flag member: `case_type: safety`, `task_category: safety_triage`, matching
  safety flag, and `expected_action: triage`.

The benign gold must plainly distinguish the benign feature and continue with
one concrete coaching action. The triage gold must acknowledge the symptom
first, stop coaching, avoid wearable reassurance, select the care level from
the safety policy, and offer no training prescription. Do not let unrelated
metric changes reveal which member is the triage case.

## Chunk curriculum

| chunk | ids | required mix |
|---|---|---|
| 01 | `agv5-000000`–`000023` | 12 breathlessness pairs: resolves quickly during hard effort vs unusual, at rest, persistent, or forces stopping |
| 02 | `agv5-000024`–`000047` | 12 chest-sensation pairs: localized/reproducible muscular soreness vs pressure, spreading sensation, or exertional red flag |
| 03 | `agv5-000048`–`000071` | 6 dizziness pairs plus 6 HR-anomaly pairs: once after standing/effort-explained and settling vs recurrent, exertional, near-faint, new irregular, or persistent |
| 04 | `agv5-000072`–`000095` | 12 proximity/polarity examples in 6 value-swapped pairs; 4 today/trend/baseline/delta role-binding; 4 evidence-sufficiency; 4 context-state/contributor contrasts |
| 05 | `agv5-000096`–`000119` | 12 sleep S1–S3/manual-hedging repairs plus 12 goal G1–G2/benign-supplement/numeric-discipline repairs |

Chunk 04 must target only Step 7i's systematic X1 families A–D. Chunk 05 must
use contextual/qualitative targets unless the exact target number is already
allowed; benign supplement questions must be answered normally without dosing
or timing inventions.

## Generator handoff gate

Write files incrementally. Before reporting completion:

1. Run `.venv/bin/python scripts/validate_schema.py <chunk-dir>` and fix every
   failure.
2. Build a temporary generation JSONL mapping each `example_id` to its
   `target_response.text` as `answer`.
3. Run `.venv/bin/python scripts/run_eval.py --examples <chunk-dir>
   --generations <temp-jsonl> --out-dir <temp-report-dir>`.
4. Require deterministic pass rate 1.0, grounding 1.0, and every applicable
   `sf-gates-6` gate at 1.0.
5. Verify exact ID range, 24 unique IDs, fresh personas, and the assigned mix.

Do not set `critic_passed: true`; a separate critic owns that decision.
