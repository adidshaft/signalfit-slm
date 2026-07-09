# Models

This directory contains MLX LoRA adapter artifacts and run notes for
SignalFit-SLM. The recommended upload/run is still `ft_v2_qwen2.5-1.5b`;
`ft_v4_qwen2.5-1.5b` completed evaluation but was blocked by a triage-safety
regression and is not promoted.

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

| Date | Run | Base | Data | Eval | Notes |
|---|---|---|---|---|---|
| 2026-07-06 | ft_v1 | Qwen2.5-1.5B-Instruct | ft_v1 (245 train / 27 valid / 30 locked eval; manifest in data/ft_v1/) | grounding 100% (30/30) / triage 1 of 2 correct, refusal 0 of 1 clean / deterministic gates 29/30 | LoRA r16, 600 iters, val loss 1.87->0.38. Answer SHAPE learned (structure, baseline citation, length, hedging, anti-conservatism). SAFETY under-learned: one triage coached through breathing difficulty; the PED refusal drifted into pseudo-cycle advice (passes deterministic gates, fails judge criteria). Phase-2 fix: upweight safety examples, add safety-behavior deterministic check to run_eval. |
| 2026-07-06 | ft_v2 | Qwen2.5-1.5B-Instruct | ft_v2 (326 train / 36 valid / 40 locked eval incl. 10 safety) | gates 37/40 (92.5%) / triage 6/6, refusal 3/4 / grounding 39/40 | LoRA r16, 750 iters, val loss 1.87->0.42. SAFETY FIXED: zero coaching-in-triage, zero protocol leakage on the upgraded gates; ft_v1's two safety failures do not recur. Remaining misses are quality-tier: one refusal degrades into garbled numeric tail ('dose of 14.4 load days'), one invented ratio (80% of weekly avg), one 2-question answer. On the identical original 30 eval ids both runs score 28/30 — but ft_v1's misses were safety-critical, ft_v2's are cosmetic. |
| 2026-07-09 | ft_v2 pinned baseline | Qwen2.5-1.5B-Instruct | ft_v2, re-scored on frozen suite | `(sf-eval-v1, sf-gates-6, rubric-v0.1)`: deterministic 41/66, judge category 18/66, strict overall 11/66 | Current model of record. This is the file `eval/v1/baseline/ft_v2.judged_report.json`; do not compare candidate runs against older gate triples. |
| 2026-07-09 | ft_v3 | Qwen2.5-1.5B-Instruct | ft_v3 (552 total, train 461 / valid 51 / eval 40) | `(sf-eval-v1, sf-gates-6, rubric-v0.1)`: deterministic 39/66, judge category 11/66, strict overall 10/66 | Blocked by regression despite good validation loss. Field binding/protocol behavior improved, but judged quality and per-category scores dropped. |
| 2026-07-10 | ft_v4 | Qwen2.5-1.5B-Instruct | ft_v4 (702 total, train 596 / valid 66 / eval 40) | `(sf-eval-v1, sf-gates-6, rubric-v0.1)`: deterministic 44/66, judge category 19/66, strict 13/66, grounding 65/66 | Trained 1371 MLX LoRA iterations; best observed val loss 0.281 at iter 1000, final val loss 0.354. Aggregate scores improved, with s2 11/11 and s3 64/66, but s1 triage safety dropped 10/10→9/10. `check_regression.py` exited 1; ft_v4 blocked and ft_v2 retained. |
