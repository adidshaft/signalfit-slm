# Independent critic report — agv7 protect

Reviewed 2026-07-12 against `agv7-qwen3-repair-1`, the training and context
schemas, `docs/eval_rubrics.md` (rubric-v0.1), and `docs/safety_policy.md`
(v0.1). Scope was limited to this `protect/` training-only slice.

## Decision

Accepted **24/24** examples. Every accepted record now has
`generation.critic_passed: true`.

- Safety positives: 7 PED/dangerous-weight-cut direct refusals and 5
  eating-disorder responses. Each names the unsafe request, gives an
  area-appropriate reason, provides no protocol/dosing/sourcing detail, and
  redirects to the appropriate support without wearable reassurance.
- Benign boundaries: 12 lookalikes answer normally, without refusal, clinician
  escalation, unsupported dosage, or an alarmist safety interpretation.

## Repairs made

Corrected the six daily-decision benign lookalikes (`012`–`017`). Their contexts
all have a null composite recovery score and no HRV/RHR/sleep signals. The
original targets did not say that, despite the generation contract's D4 rule;
some also left more than one next action. The repaired targets now explicitly
bound their reasoning to the unavailable recovery data plus the reported facts,
lead with a recommendation level, and give exactly one concrete next action.

No unsafe safety-positive response needed repair. No record was rejected.

## Verification

- `.venv/bin/python scripts/validate_schema.py .../protect`: **24 passed, 0
  failed**.
- Gold calibration generated from the reviewed target responses and run through
  `scripts/run_eval.py`: **24/24 deterministic**, **24/24 grounding** at
  `sf-gates-10` / `rubric-v0.1`.
- Applicable safety gates: s2 refusal **7/7**, s1 triage **5/5**. All x1, x4,
  x5, x6, s3, s4, and s5 checks passed **24/24**.
