# Models

No model artifacts yet — design phase.

## Planned

- Base: a 1–8B open-weights instruct model suitable for on-device inference
  (candidates to be benchmarked; selection criteria in `docs/eval_plan.md`).
- Fine-tune: SFT on `data/synthetic/curated/` via `training/mlx/` (Apple Silicon)
  or `training/unsloth/` (CUDA), configs in `training/configs/`.
- Every run directory here must include: base model id + revision, dataset manifest
  hash, training config, eval report against the locked eval set, and a short
  run-notes file (what changed, why, verdict).

## Run log

| Date | Run | Base | Data | Eval (grounding / safety recall / false-refusal) | Notes |
|---|---|---|---|---|---|
| — | — | — | — | — | no runs yet |
