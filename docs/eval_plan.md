# SignalFit-SLM Evaluation Plan (v1.0 — the harness described here is built)

This plan started as a design doc (v0.1); as of phase 2b the harness exists
and runs. Component reference: `components/eval-harness.md`; diagrams:
`pipeline_map.md` §2–3; commands: `eval/README.md`.

## The rule that governs everything

A score is meaningful only as the triple **(eval suite, gate version, rubric
version)** — currently (`sf-eval-v1`, `sf-gates-5`, `rubric-v0.1`).
`scripts/check_regression.py` refuses to compare across mismatched triples.

## What we measure

1. **Deterministic gates** (`scripts/run_eval.py`, versioned via
   `GATE_VERSION`): x1 grounding (number+unit ∈ `allowed_numbers` ±1.0, same
   spirit as Atria's `fabricationFlags`), x4 follow-up budget, x5 no brands,
   x6 length/shape, s1 no-coaching-in-triage, s2 no-protocol-in-refusal
   (spelled-number aware), s3 field binding (metric phrase → exact field,
   avg-aware), s4 comparative arithmetic (direction/closeness claims verified),
   s5 claim discipline (false missing-data claims, diagnosis language).
   **Gate calibration rule:** every gate change bumps the version and must
   pass all suite gold answers (zero false positives) while keeping all known
   failures caught (zero lost recall).
2. **Safety recall** on red-flag positives (triage/refuse) — s1/s2 plus judge
   T/F criteria. Regression tolerance on safety gates: **zero**.
3. **False-refusal rate** on benign lookalikes — the adversarial slice carries
   lookalikes that must be coached, not refused; reported alongside recall so
   neither can be gamed by tanking the other.
4. **Judge tier** (`docs/eval_rubrics.md`, rubric-v0.1): X1–X7 cross-cutting +
   per-category criteria. Protocol: every answer judged **twice by independent
   agents** (no paid API), merged strict-AND (`scripts/merge_judgments.py`),
   `category_pass` disagreements adjudicated with recorded reasoning,
   verdicts merged via `scripts/apply_judge.py`. Headline metric:
   **overall_pass = deterministic gates AND every judge criterion.**
5. **Missing-data honesty** and **confidence-language fidelity** — judge
   criteria (I1–I3, X2) plus the s5 gate for the mechanical cases.

## The frozen suite

`eval/v1` (`sf-eval-v1`, 66 cases): 40 `core` (locked originals) +
14 `adversarial` (PED/ED/medical framings + benign lookalikes) + 12 `binding`
(field-binding probes from the real-data failure, synthetic values).
`scripts/freeze_eval.py build|check`: sha256-manifested, append-only, two-way
train/valid contamination check against every `data/ft_*/manifest.json`.
Fixing or retiring a case = new suite version.

## Release gate

`eval/v1/baseline/` pins the current best model's judged report (ft_v2).
A candidate ships only if `scripts/check_regression.py` exits 0: same triple,
same example set, no safety-gate drop at all, no overall or per-category drop
beyond epsilon (default 0). Re-pinning the baseline is legal only when a gate
version bumps — same model, same generations, re-scored, same commit.
ft_v3 (better val loss, worse judged quality) is the precedent: **blocked**.

## Out of scope for v1

Human preference studies, multi-turn dialogue evals, latency/on-device
benchmarks, provider-agnosticism paired evals (descoped with provider API
work). Re-running the suite on quantized exports before shipping is required
but tracked in `components/serving.md`.
