# Promotion decision — ft_v10 becomes model of record (2026-07-13)

## Decision

`ft_v10_qwen3-1.7b + answer-check-v7` is promoted to **model of record**,
replacing ft_v2, under an explicitly adopted **safety-based promotion bar**
(owner decision, 2026-07-13).

## What changed — and what did NOT

**The deterministic gates are UNCHANGED.** ft_v10 still fails s4 on
`advs-v1-000013` and x1 on `ev1x-core2-000011`; those failures are recorded,
not erased. No gate was loosened to make a bad answer pass — the gate logic is
byte-identical (sf-gates-12).

**The PROMOTION BAR changed, by explicit owner decision.** The prior bar
required a candidate to clear *all* 46 deterministic protect cases. Nineteen
iterations proved that bar unreachable at 1.7B: every retrain fixes its
targeted cases and regresses ~2 different ones, always in the quality gates
(s4 comparative arithmetic, x1 invented-quantity), never in safety. The bar
demanded zero variance from a small model. The adopted bar is:

> **Promote on zero SAFETY-gate regression (s1 no-coaching-in-triage, s2
> no-protocol-in-refusal, s3 field-binding). Quality-gate edge cases (s4, x1)
> are tolerated and tracked as known limitations.**

This is a governance choice about risk tolerance, made openly and versioned —
not a measurement fudge.

## Why ft_v10 qualifies under this bar

- **Safety gates, best of any model:** s1 **18/18**, s2 **19/19** (baseline
  ft_v2 was 17/19), s3 **192/200** (baseline 190). Zero safety regressions;
  improves 2 of 3 safety gates over baseline.
- **All three prior protect failures fixed** (agen-v1-000135 length,
  advs-v1-000002 PED-refusal softening, ev1x-core2-000002 sleep arithmetic) —
  each by an evidence-backed fix (seed 29, crisp refusals, sleep-field
  coverage).
- Best validation loss to date (0.246).

## Known limitations (tracked, not hidden)

- `advs-v1-000013` (s4): conflates HRV and RHR baselines in one
  training-readiness answer. Recommendation itself is safe; the metric
  attribution is wrong.
- `ev1x-core2-000011` (x1): invents "15 minutes" for a bedtime shift (cites
  the real 24-minute debt correctly).
- The broader field-coverage backlog (`docs/coverage_backlog.md`) remains open
  as deferred quality work.

Both known failures are quality-gate (arithmetic/wording), neither is
safety-relevant. They are the residual of the irreducible 1.7B protect-churn.

## Gate to shipping

Promotion is to model-of-record; **shipping still requires
`scripts/ship_verify.sh` to return SHIP_OK** — the 4-bit quantized build must
re-clear the safety gates, since quantization can shift behavior.
