# MLX fine-tuning (Apple Silicon)

Status: **prepared, not run** — training starts only on explicit confirmation.

## One-time setup

```bash
.venv/bin/pip install mlx-lm            # Apple-Silicon-only; pulls mlx
.venv/bin/python -c "import mlx_lm; print(mlx_lm.__version__)"
```

The base model downloads from Hugging Face on first use (no separate step needed);
to pre-fetch: `.venv/bin/huggingface-cli download Qwen/Qwen2.5-1.5B-Instruct`.

## Run ft_v0 (smoke run on the seed dataset)

```bash
# 1. (Re)build the dataset deterministically
.venv/bin/python scripts/generate_seed_dataset.py --out data/synthetic/curated/seed_v0
.venv/bin/python scripts/validate_schema.py data/synthetic/curated/seed_v0 data/synthetic/curated/worked_examples
.venv/bin/python scripts/prepare_dataset.py data/synthetic/curated/seed_v0 data/synthetic/curated/worked_examples -o data/ft_v0/all.jsonl
.venv/bin/python scripts/split_dataset.py data/ft_v0/all.jsonl --out-dir data/ft_v0

# 2. Train LoRA adapters (~minutes for 200 iters on an M-series Mac)
.venv/bin/mlx_lm.lora --config training/configs/mlx_lora_qwen2.5-1.5b-instruct.yaml

# 3. Quick qualitative check
.venv/bin/mlx_lm.generate --model Qwen/Qwen2.5-1.5B-Instruct \
  --adapter-path models/adapters/ft_v0_qwen2.5-1.5b \
  --prompt "$(python3 -c "import json;line=json.loads(open('data/ft_v0/eval.jsonl').readline());print(line['messages'][1]['content'])")"

# 4. Optional: fuse adapters into a standalone model
.venv/bin/mlx_lm.fuse --model Qwen/Qwen2.5-1.5B-Instruct \
  --adapter-path models/adapters/ft_v0_qwen2.5-1.5b \
  --save-path models/fused/ft_v0_qwen2.5-1.5b
```

## Export for on-device iOS use (after fuse)

```bash
.venv/bin/mlx_lm.convert --hf-path models/fused/ft_v0_qwen2.5-1.5b \
  -q --q-bits 4 --q-group-size 64 \
  --mlx-path models/export/ft_v0_qwen2.5-1.5b-4bit
```

The quantized folder loads directly in **MLX Swift** (`MLXLLM` from
mlx-swift-examples) on Apple Silicon iPhones — same ecosystem end to end, no
Core ML conversion. Full integration contract (chat shape, context building,
on-device grounding check): docs/process_guide.md §8.

Rules: `data/ft_v0/eval.jsonl` never enters training; every run is logged in
`models/README.md` with the dataset manifest hash; ft_v0 is a **pipeline smoke
run** — expect memorization, not quality (25 train examples).

## Purpose of ft_v0

Prove: data format loads, loss falls, adapters save, generation obeys the chat
template. Real quality work starts with the frontier-generated dataset
(docs/data_generation_plan.md) on the same pipeline.
