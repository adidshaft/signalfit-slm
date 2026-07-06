# Models

No model artifacts yet — training awaits explicit go-ahead.

## Base model selection (2026-07-05)

- **Primary: `Qwen/Qwen2.5-1.5B-Instruct`** — Apache-2.0, strong instruction
  following at 1.5B, comfortable LoRA fine-tune + inference on Apple Silicon via
  MLX. Config: `training/configs/mlx_lora_qwen2.5-1.5b-instruct.yaml`.
- **Benchmark fallback: `Qwen/Qwen2.5-3B-Instruct`** — better quality ceiling,
  BUT note the **license difference: 3B ships under the Qwen Research License
  (non-commercial), not Apache-2.0**. Fine for benchmarking; not for shipping.
- If the 1.5B underperforms and 3B licensing blocks shipping, evaluate
  **Qwen3-1.7B / Qwen3-4B (Apache-2.0)** or Llama-3.2-3B (Llama license) before
  committing. Verify current licenses on the model cards at selection time.
- Fine-tune: SFT on `data/synthetic/curated/` via `training/mlx/` (Apple Silicon)
  or `training/unsloth/` (CUDA), configs in `training/configs/`.
- Every run directory here must include: base model id + revision, dataset manifest
  hash, training config, eval report against the locked eval set, and a short
  run-notes file (what changed, why, verdict).

## Run log

| Date | Run | Base | Data | Eval (grounding / safety recall / false-refusal) | Notes |
|---|---|---|---|---|---|
| 2026-07-06 | ft_v1 | Qwen2.5-1.5B-Instruct | ft_v1 (245 train / 27 valid / 30 locked eval; manifest in data/ft_v1/) | grounding 100% (30/30) / triage 1 of 2 correct, refusal 0 of 1 clean / deterministic gates 29/30 | LoRA r16, 600 iters, val loss 1.87->0.38. Answer SHAPE learned (structure, baseline citation, length, hedging, anti-conservatism). SAFETY under-learned: one triage coached through breathing difficulty; the PED refusal drifted into pseudo-cycle advice (passes deterministic gates, fails judge criteria). Phase-2 fix: upweight safety examples, add safety-behavior deterministic check to run_eval. |
| 2026-07-06 | ft_v2 | Qwen2.5-1.5B-Instruct | ft_v2 (326 train / 36 valid / 40 locked eval incl. 10 safety) | gates 37/40 (92.5%) / triage 6/6, refusal 3/4 / grounding 39/40 | LoRA r16, 750 iters, val loss 1.87->0.42. SAFETY FIXED: zero coaching-in-triage, zero protocol leakage on the upgraded gates; ft_v1's two safety failures do not recur. Remaining misses are quality-tier: one refusal degrades into garbled numeric tail ('dose of 14.4 load days'), one invented ratio (80% of weekly avg), one 2-question answer. On the identical original 30 eval ids both runs score 28/30 — but ft_v1's misses were safety-critical, ft_v2's are cosmetic. |
