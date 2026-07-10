# Models

This directory contains MLX LoRA adapter artifacts and run notes for
SignalFit-SLM. The recommended upload/run is still `ft_v2_qwen2.5-1.5b`;
`ft_v4_qwen2.5-1.5b` completed evaluation but was blocked by a triage-safety
regression and is not promoted. `ft_v5_qwen2.5-1.5b` is also blocked: its
deterministic score improves after the sf-gates-7/8 corrections, but strict
judged quality still regresses.

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
| 2026-07-09 | ft_v2 pinned baseline | Qwen2.5-1.5B-Instruct | ft_v2, re-scored on frozen suite | `(sf-eval-v1, sf-gates-10, rubric-v0.1)`: deterministic 41/66, judge category 18/66, strict overall 11/66 | Current model of record, re-pinned after the s1/s3/s4 parser corrections. This is `eval/v1/baseline/ft_v2.judged_report.json`; do not compare candidate runs against older gate triples. |
| 2026-07-11 | ft_v2 expanded baseline | Qwen2.5-1.5B-Instruct | same ft_v2 adapter; 134 appended cases generated and judged | `(sf-eval-v1, sf-gates-10, rubric-v0.1)`: deterministic 101/200, judge category 46/200, strict overall 30/200 | Sanctioned suite-expansion re-pin. Existing 66 answers/verdicts were reused; the 134 new cases received two independent passes plus 21 third-pass adjudications. `eval/v1/baseline/ft_v2.judged_report.json` is now the current 200-case regression bar; the prior 66-case artifact is retained beside it. |
| 2026-07-09 | ft_v3 | Qwen2.5-1.5B-Instruct | ft_v3 (552 total, train 461 / valid 51 / eval 40) | `(sf-eval-v1, sf-gates-6, rubric-v0.1)`: deterministic 39/66, judge category 11/66, strict overall 10/66 | Blocked by regression despite good validation loss. Field binding/protocol behavior improved, but judged quality and per-category scores dropped. |
| 2026-07-10 | ft_v4 | Qwen2.5-1.5B-Instruct | ft_v4 (702 total, train 596 / valid 66 / eval 40) | `(sf-eval-v1, sf-gates-10, rubric-v0.1)`: deterministic 45/66, judge category 19/66, strict 13/66, grounding 65/66 | s3 role parsing corrects two false positives and reaches 66/66, but the real s1 triage failure remains 9/10. `check_regression.py` exits 1; ft_v4 blocked and ft_v2 retained. |
| 2026-07-10 | ft_v5 | Qwen2.5-1.5B-Instruct | ft_v5 weighted (894 rows / 822 unique; train 769 / valid 85 / eval 40) | `(sf-eval-v1, sf-gates-10, rubric-v0.1)`: deterministic 51/66, judge category 18/66, strict 10/66, grounding 65/66 | s1 is 10/10, s3 65/66, s4 52/66, and s5 66/66. Strict overall, sleep, goal, and refusal still regress; `check_regression.py` exits 1, so ft_v5 remains blocked and ft_v2 retained. |
| 2026-07-10 | ft_v6 s11/r16/i1238 | Qwen2.5-1.5B-Instruct | fixed ft_v5 data | `(sf-eval-v1, sf-gates-10, rubric-v0.1)`: deterministic 44/66; prefilter reject | Best/final val 0.198/0.310. Rejected before judging on s1 9/10 and protected `agen-v1-000231`. |
| 2026-07-10 | ft_v6 s29/r16/i2300 | Qwen2.5-1.5B-Instruct | fixed ft_v5 data | `(sf-eval-v1, sf-gates-10, rubric-v0.1)`: deterministic 49/66, judge category 17/66, strict 9/66; blocked | Prefilter survivor with s1 10/10, s2 11/11, s3 66/66 and all 11 protect ids deterministic. Double judging then exposed strict 11→9, safety triage 4→3, and daily decision 1→0; no promotion. |
| 2026-07-10 | ft_v6 s41/r32/i1238 | Qwen2.5-1.5B-Instruct | fixed ft_v5 data | `(sf-eval-v1, sf-gates-10, rubric-v0.1)`: deterministic 48/66; prefilter reject | Best/final val 0.223/0.246. Aggregate safety floors pass, but protected `safe-v2-000093` reverses recovery 62% versus its 64% average; rejected before judging. |
| 2026-07-10 | ft_v6 s53/r32/i2300 | Qwen2.5-1.5B-Instruct | fixed ft_v5 data | `(sf-eval-v1, sf-gates-10, rubric-v0.1)`: deterministic 47/66; prefilter reject | Best/final val 0.221/0.221. A demonstrated s4 cross-metric false positive was corrected, but protected `agen-v1-000231` still overstates HRV 46 vs 50.4 as close; rejected before judging. |
| 2026-07-10 | ft_v6 Qwen3.5-2B preflight | Qwen3.5-2B | fixed ft_v5 data | inference smoke only; training aborted | Apache-2.0 and direct non-thinking inference work, but one LoRA step exhausted 24 GB and remained incomplete after several minutes. Locally unusable; no candidate score claimed. |
| 2026-07-10 | ft_v6 Qwen3-1.7B fallback | Qwen3-1.7B | fixed ft_v5 data | `(sf-eval-v1, sf-gates-10, rubric-v0.1)`: deterministic 48/66, judge category 19/66, strict 14/66; blocked | Apache-2.0. Full 1,769-step run: best observed val 0.236, 15.550 GB peak. Aggregate strict and safety triage improve, but sleep strict falls 1/6→0/6, daily decision 1/9→0/9, and lookalikes reach only 1/7 strict. Regression exits 1; ft_v2 retained. |
