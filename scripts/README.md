# Script guide

Scripts are grouped here by workflow. Run commands from the repository root so
their path assumptions remain valid.

## Serving and model checks

- `answer_with_check.py`: production-style checked inference
- `ask.py`: low-level qualitative adapter query; defaults are historical
- `check_model.py`: local candidate evaluation orchestration
- `ship_verify.sh`: final fuse, quantize, evaluate, and ship verification

## Data preparation

- `generate_seed_dataset.py`, `make_context_specs.py`: deterministic sources
- `prepare_dataset.py`, `split_dataset.py`: chat conversion and splits
- `validate_schema.py`: schema, grounding, and missing-field validation

## Evaluation

- `freeze_eval.py`: frozen-suite manifest and contamination checks
- `generate_answers.py`, `run_eval.py`: generation and deterministic scoring
- `apply_judge.py`, `merge_judgments.py`: judgment application and agreement
- `check_regression.py`, `check_sweep_candidate.py`: promotion gates

## Judge and owner-review protocols

- `judge_protocol.py`, `judge_protocol_v2.py`, `judge_v2_orchestrator.py`
- `build_owner_review_packet.py`, `apply_owner_review.py`

Historical iteration generators remain named by their training round for exact
reproducibility. See [`../docs/project_history.md`](../docs/project_history.md)
before modifying them.
