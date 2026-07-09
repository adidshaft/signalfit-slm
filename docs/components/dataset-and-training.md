# Dataset Build & Training — curated JSON → chat JSONL → LoRA adapter

## Dataset build (deterministic, manifest-hashed, safe to re-run)

| Component | Job | Key rule |
|---|---|---|
| `scripts/prepare_dataset.py` | example JSON → `sf-chat-1` chat JSONL | Strips the question duplicate and the `task` label from the model input (the model must not see its category); pins system prompt `sft-sys-1`; writes a sidecar manifest with per-line example_id/labels/sha256 + file sha256. |
| `scripts/split_dataset.py` | train / valid / eval split | **Persona-disjoint** train/valid (validation measures generalization, not memory); locked eval isolated — `is_locked_eval` examples and their personas never enter train/valid; split recorded in `manifest.json` with per-split example_ids + hashes. |
| `data/ft_v0 … ft_v3` | one directory per training generation | `all.jsonl` + manifests + splits + that generation's eval artifacts. ft_v2 = 402 lines (agent_v1 + agent_v2_safety + worked); ft_v3 = 552 (…+ agent_v3_relational) → train 461 / valid 51 / eval 40. |

The manifests are what make everything auditable: the eval-suite freezer
(`freeze_eval.py`) cross-checks its case ids against every
`data/ft_*/manifest.json` train/valid split, both ways, on every build and
check — eval contamination is structurally blocked, not just discouraged.

## Base model choice

- **Primary: Qwen2.5-1.5B-Instruct** — Apache-2.0, LoRA-trainable on an
  M-series Mac, ~1 GB once 4-bit quantized (iPhone-viable).
- **Qwen2.5-3B-Instruct** — better ceiling but **Qwen Research License
  (non-commercial)** → benchmark-only, never ship.
- Escape hatch: Qwen3-1.7B/4B (Apache-2.0).

**Lesson:** licenses vary *within* a model family by size — check per size.

## LoRA on MLX

LoRA trains small adapter matrices over frozen base weights: minutes per run,
~20 MB artifacts. Configs live in `training/configs/` (one YAML per run,
committed); adapters land in `models/adapters/` (gitignored — artifacts, not
source); training logs in `models/*_train.log`.

| Run | Data | Iterations | Val loss | Eval verdict |
|---|---|---|---|---|
| ft_v1 | 245 train (agent_v1) | 600 | 1.87 → 0.38 | shape learned, safety under-learned |
| ft_v2 | 326 train (+safety round) | 750 | → 0.42 | safety fixed; **pinned baseline / model of record** |
| ft_v3 | 461 train (+relational round) | 1060 | → 0.284 | ⛔ blocked by regression gate |

Rules of thumb from these runs: `iters ≈ 2.3 × train_count` (~2–2.5 epochs);
~10–20 min and ~10 GB peak RAM at batch 1 / seq-len 3072 on an M-series Mac.
Note ft_v3: the **best validation loss of the three** and still a net eval
regression — val loss measures fit to the data distribution, the frozen suite
measures what we actually want. Only one of them can block a release.

## Reproduce-it commands

The full command chain (venv setup → validate → prepare → split → train →
eval) is maintained in `docs/using_and_finetuning.md` §5–6; the per-phase
narrative with lessons is `docs/process_guide.md` Step 6 / 6b.
