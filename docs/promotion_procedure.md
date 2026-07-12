# Promotion procedure (how a candidate becomes the shipped model)

Resolves an ambiguity in the finish line: the iteration-15 owner-review packet
was built on **LLM judge verdicts** (`candidate overall_pass`), but this
project **retired LLM judging** as untrustworthy (iterations 13–14). New
candidates (ft_v10 onward) have only a **deterministic** eval report. This
document pins down promotion without judging.

## The gate sequence

1. **Deterministic prefilter (`check_sweep_candidate.py`) — MUST pass.**
   Candidate must clear: aggregate deterministic ≥ baseline, every safety-gate
   rate ≥ baseline, all 30 ft_v2 strict protects, all 16 prior strict-gain
   protects. This is fully deterministic and needs no judge. A fail here stops
   promotion; no human review is spent on a candidate that regresses a protect.

2. **Owner review (human adjudication) — the promotion decision.**
   Only if the prefilter passes. The blinded A/B owner-review-v1 instrument
   still applies, with ONE adaptation for the no-judge reality:

   - **Difference pairs** are selected where the candidate's **deterministic
     pass** differs from the baseline's frozen **judged** outcome — i.e.
     `baseline.overall_pass == True and candidate.deterministic_pass == False`
     (candidate-worse cases the human checks for real regressions) and the
     reverse for gains. This swaps the candidate's `overall_pass` (judge) for
     `deterministic_pass` in `build_owner_review_packet.py` — a one-field
     change, to be made against the candidate's real report, not pre-guessed.
   - The human then adjudicates **candidate answer quality directly**, blinded.
     This is exactly what the owner-review instrument is for; the judge was
     only ever used to *select* which cases to show, never to decide quality.
   - Predeclared thresholds and sealed A/B mapping are unchanged from 15A.

   If the reviewer's verdict is PROMOTE, the candidate becomes the new model of
   record.

3. **Ship verification (`scripts/ship_verify.sh`) — MUST pass.**
   Fuse → 4-bit quantize → re-run the prefilter on the QUANTIZED model. Ships
   only on SHIP_OK (the quantized build clears the same protects). This is the
   last gate; quantization can degrade behavior.

## Shortcut for a clean sweep

If the prefilter shows the candidate clears **all 46 protects AND** loses zero
cases the baseline's frozen judgments passed (no difference-pair losses at all),
the owner review has nothing adverse to adjudicate — the candidate is
strictly ≥ baseline on every measured axis. In that case the owner review is a
confirmation formality, and ship verification is the binding remaining gate.

## Why this is trustworthy without a judge

The deterministic gates (sf-gates-12) encode every safety and grounding rule as
fossilized past failures; the protect sets guarantee no regression against the
baseline's human-approved answers; and the human owner review adjudicates the
candidate's actual answer quality on exactly the cases that changed. No step
relies on the LLM judge that failed its trust gates.
