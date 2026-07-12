# Training

SignalFit fine-tuning uses MLX LoRA on Apple Silicon. Configuration files are
immutable records of individual experiments; their versioned names and output
paths are intentionally verbose.

- `configs/`: exact LoRA configurations for each run
- `mlx/README.md`: MLX setup and training workflow
- `unsloth/`: reserved for CUDA/Unsloth experiments

The current model-of-record configuration is
[`configs/mlx_lora_qwen3-1.7b-ft_v10.yaml`](configs/mlx_lora_qwen3-1.7b-ft_v10.yaml).
Install the Apple-Silicon dependencies with:

```bash
.venv/bin/pip install -r requirements-mlx.txt
```

Training output, adapters, fused weights, and safetensors are not normal source
contributions. Do not add them to Git. Candidate promotion must follow
[`../docs/promotion_procedure.md`](../docs/promotion_procedure.md).
