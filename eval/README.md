# Frozen eval suites

A suite version (`eval/v1/`, `eval/v2/`, …) is an immutable set of eval cases.
Scores are meaningful ONLY as a triple: **(suite version, gate version, rubric
version)**. Two numbers may be compared iff all three match — that is enforced,
not just documented (`scripts/check_regression.py` exits 1 on any mismatch).

## Layout

```
eval/v1/
  manifest.json            # per-case sha256 + slice/category labels (frozen)
  gold_generations.jsonl   # gold answers of every case, for gate calibration
  cases/
    core/                  # the 40 locked eval examples ft_v1/ft_v2 were scored on
    adversarial/           # adversarial safety: framings engineered to lure the
                           # model out of policy (PED/ED/medical) + benign
                           # lookalikes that must NOT be refused
    binding/               # field-binding probes: decimal sensor-realistic values,
                           # confusable field pairs, today-vs-trend traps, derived
                           # deltas in allowed_numbers (from the real-data failure)
  baseline/                # pinned reports of the current best model — the bar
                           # every new model must meet through check_regression.py
```

## Rules

1. **Frozen means frozen.** A case that has ever been in a suite version never
   changes and never disappears. `scripts/freeze_eval.py build` refuses edits;
   `check` re-hashes everything. Fixing/retiring a case = new suite version.
2. **Append-only slices.** New slices may be added to an existing version (old
   scores on old slices stay comparable; full-suite scores restart at the
   moment of addition — record it in models/README.md).
3. **No train/valid contamination.** `freeze_eval.py` cross-checks every case
   id against all `data/ft_*/manifest.json` train/valid splits, both ways, on
   every build and check.
4. **Gate changes bump `GATE_VERSION`** in `scripts/run_eval.py` and require
   recalibration: gold answers of the whole suite must pass 100%
   (no false positives) and all previously-caught failures must stay caught
   (no lost recall) before the new version is used for scoring.
5. **Real personal data never enters a suite.** Real exports stay local-only
   under `data/real_world/` (see its README). What a real-data failure
   contributes to the suite is its *shape*, rebuilt with synthetic values
   (that is exactly what `cases/binding/` is).

## Scoring a model through the suite

```bash
# 1. answers
.venv/bin/python scripts/generate_answers.py \
    --examples eval/v1/cases/core eval/v1/cases/adversarial eval/v1/cases/binding \
    --adapter models/adapters/<run> -o <out>/suite_generations.jsonl

# 2. deterministic gates + judge bundle
.venv/bin/python scripts/run_eval.py --examples eval/v1/cases \
    --generations <out>/suite_generations.jsonl --out-dir <out>/eval_report

# 3. LLM judge: every answer judged twice, independently (agent workflow —
#    no paid API), then merged; category_pass disagreements are adjudicated
#    by a human (or third judge) and appended.
.venv/bin/python scripts/merge_judgments.py --pass-a <a.jsonl> --pass-b <b.jsonl> \
    --out <out>/judge_verdicts.jsonl --disagreements <out>/disagreements.jsonl
.venv/bin/python scripts/apply_judge.py --report <out>/eval_report/eval_report.json \
    --verdicts <out>/judge_verdicts.jsonl --out <out>/eval_report/judged_report.json

# 4. regression gate vs the pinned baseline (exit 1 blocks the model)
.venv/bin/python scripts/check_regression.py \
    --baseline eval/v1/baseline/<current>.judged_report.json \
    --candidate <out>/eval_report/judged_report.json

# integrity check any time (CI-style):
.venv/bin/python scripts/freeze_eval.py check --version v1
```
