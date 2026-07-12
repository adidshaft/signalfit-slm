# Contributing to SignalFit-SLM

Thanks for helping improve grounded, privacy-conscious fitness coaching. This
repository welcomes fixes, tests, documentation, provider adapters, evaluation
cases, and carefully scoped model or data improvements.

## Before you start

- Search existing issues and pull requests before opening a duplicate.
- Use an issue for substantial behavior, schema, safety, or evaluation changes.
- Never commit real wearable exports, health records, credentials, model
  weights, or other private data.
- Read [`docs/safety_policy.md`](docs/safety_policy.md) before changing model
  behavior and [`docs/eval_plan.md`](docs/eval_plan.md) before changing gates.

## Development setup

SignalFit's deterministic tooling and tests run on Python 3.10 or newer.
MLX inference and training require Apple Silicon.

```bash
git clone https://github.com/adidshaft/signalfit-slm.git
cd signalfit-slm
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v
```

For local model inference or training:

```bash
.venv/bin/pip install -r requirements-mlx.txt
```

## Repository map

- `schemas/`: versioned input and training-example contracts
- `scripts/`: data, evaluation, serving, and release tools
- `tests/`: deterministic unit and integration tests
- `eval/v1/`: frozen evaluation suite and manifests
- `data/synthetic/`: synthetic source data; no real health exports
- `training/configs/`: reproducible MLX LoRA configurations
- `docs/`: architecture, policy, evaluation, and historical decisions
- `benchmarks/`: reproducible benchmark inputs, outputs, and reports

The full documentation index is in [`docs/README.md`](docs/README.md).

## Making a change

1. Branch from `main`.
2. Keep the change focused and avoid moving frozen artifacts without a strong
   reason; many manifests and scripts intentionally use stable paths.
3. Add or update tests for behavior changes.
4. Run `make check`. For schema or dataset changes, also run the validator on
   the affected examples.
5. Update documentation when a command, contract, or result changes.
6. Open a pull request using the repository template.

## Safety and evaluation invariants

Changes must preserve these rules:

- Answers may cite only values represented by `allowed_numbers`.
- Medical red flags stop coaching and redirect to real-world care.
- Frozen evaluation cases are append-only and manifest checked.
- Gate or rubric changes require a version bump and calibration.
- Candidate reports are comparable only when their suite, gate, rubric, and
  judge-protocol versions match.
- Model promotion follows [`docs/promotion_procedure.md`](docs/promotion_procedure.md).

Do not modify expected answers or gates merely to improve a candidate score.
Document the observed failure and address its root cause.

## Data contributions

Only synthetic, licensed, or explicitly authorized data may be contributed.
Replace any personal values with wholly synthetic examples. Do not derive
synthetic rows by lightly perturbing a real person's health export.

Validate training examples with:

```bash
.venv/bin/python scripts/validate_schema.py path/to/examples
```

## Pull request checklist

- The diff contains no private data, secrets, or model weights.
- Tests pass locally.
- Frozen manifests still validate.
- New numbers in model answers are represented in `allowed_numbers`.
- Safety-sensitive changes include focused regression tests.
- Documentation and changelog-style decision records are updated when needed.

By submitting a contribution, you agree that it is licensed under the Apache
License 2.0 found in [`LICENSE`](LICENSE).
