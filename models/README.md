# Models

This directory contains MLX LoRA adapter artifacts and run notes for
SignalFit-SLM.

**Model of record (2026-07-13): `ft_v10_qwen3-1.7b` + `answer-check-v7`.**
Promoted from ft_v2 under the owner-adopted **safety-based promotion bar**
(`docs/PROMOTION_DECISION_ft_v10.md`, `docs/promotion_procedure.md`): after 19
iterations proved the all-46-deterministic-protect bar unreachable at 1.7B
(irreducible protect-churn in the s4/x1 quality gates), the owner adopted a bar
that requires zero SAFETY-gate regression and tolerates quality-gate edge cases
as tracked known limitations. ft_v10 has the best safety profile of any model
(s1 18/18, s2 19/19, s3 192/200 — improving 2 of 3 over baseline), fixed all
three prior protect failures, and best validation loss to date (0.246). Known
quality limitations: `advs-v1-000013` (s4 HRV/RHR conflation),
`ev1x-core2-000011` (x1 invented bedtime-shift). The deterministic gates were
never loosened; only the promotion threshold changed. Shipping requires
`scripts/ship_verify.sh` -> SHIP_OK on the 4-bit quantized build.

`ft_v2_qwen2.5-1.5b` (Qwen2.5-1.5B) is the prior model of record and remains
the pinned regression baseline (`eval/v1/baseline/ft_v2.judged_report.json`).
The iterations that kept it as record until now: iteration 15's owner-review-v1
returned DO_NOT_PROMOTE for the ft_v7-micro+wrapper-v4 candidate (difference
14/19, preference 15-3-1 for ft_v2); iterations 16A-18A hit prefilter stops.
ft_v10 (iteration 19) is the first promotion.

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
| 2026-07-11 | ft_v7 Qwen3.5-2B 4-bit QLoRA smoke | Qwen3.5-2B @ `15852e8` | fixed ft_v5 data | technical block; no candidate score | Exact source converted to 1.0 GB MLX 4-bit base (4.503 bits/weight). Model/data load and validation pass, but the first train command buffer aborts `Insufficient Memory`; host peak footprint 21.34 GB. No further capacity retry under the iteration protocol. |
| 2026-07-10 | ft_v6 Qwen3-1.7B fallback | Qwen3-1.7B | fixed ft_v5 data | `(sf-eval-v1, sf-gates-10, rubric-v0.1)`: deterministic 48/66, judge category 19/66, strict 14/66; blocked | Apache-2.0. Full 1,769-step run: best observed val 0.236, 15.550 GB peak. Aggregate strict and safety triage improve, but sleep strict falls 1/6→0/6, daily decision 1/9→0/9, and lookalikes reach only 1/7 strict. Regression exits 1; ft_v2 retained. |
| 2026-07-11 | ft_v6 Qwen3-1.7B expanded | Qwen3-1.7B | fixed ft_v5 data | `(sf-eval-v1, sf-gates-10, rubric-v0.1)`: deterministic 123/200, judge category 58/200, strict 29/200; blocked | New 134 cases generated and double-judged; 57 category disagreements received third-pass adjudication. Safety gates hold, but refusal, daily, and sleep strict regress against the 200-case ft_v2 baseline. |
| 2026-07-11 | Qwen3-1.7B + verify/retry-1 | Qwen3-1.7B system | same adapter plus one deterministic retry | deterministic 139/200, judge category 62/200, strict 30/200; blocked | 76/200 drafts retried (median 3.72 s, p95 5.45 s); unchanged answers reuse the bare verdict and changed answers receive independent double judging + 18 third-pass adjudications. It ties ft_v2 strict aggregate but refuses to clear because refusal falls 11→8 and daily 1→0. |
| 2026-07-11 | ft_v7 Qwen3-1.7B repair | Qwen3-1.7B | ft_v7 (920 train / 102 valid / 40 eval; 120 repair rows repeated 2×) | deterministic 119/200; prefilter reject | Full 2,116-step r16 run, 15.7 GB observed peak. Aggregate/safety floors clear (s1 18/18, s2 18/19, s3 193/200), but four of 30 protected ft_v2 cases fail: one X6 refusal length and three X1/s4 comparison errors. No judging or promotion. |
| 2026-07-11 | ft_v7 micro + verify/retry-1 | Qwen3-1.7B system | ft_v7 plus 28 unique residue examples (945 train / 105 valid / 40 eval) | deterministic 144/200; dual-protect reject | Full unchanged 2,116-step r16 run, final val 0.373, 15.55 GB peak. The fresh system fixes all four original ft_v7 protect failures and retries 71/200 (35.5%; all-case 4.13/12.72 s median/p95), but loses protected benign length case `ev1x-lookalike2-001` and safety-critical triage case `advs-v1-000007`. No judge, promotion, fusion, or quantization; ft_v2 retained. |
| 2026-07-11 | iteration 10 Qwen3.5-2B measured-memory ladder | Qwen3.5-2B @ `15852e8` local 4-bit | ft_v7_micro measured at train max/p95 2,249/2,157 tokens | technical block; no candidate score | Apache-2.0 reverified. With gradient checkpointing, the true 2,249-token maximum OOMs at 23.90 GB r16/16, 22.65 GB r8/8, and 21.80 GB r4/4. A lossless-subset 1,895-token row still OOMs at 23.06 GB r16/16 and 21.21 GB r4/4. No credible full adapter trained; evaluation stops before prefilter/judging and ft_v2 remains pinned. |
| 2026-07-12 | iteration 11 Gemma 4 E2B preflight | Gemma 4 E2B @ `9dbdf8a` | no training | technical block; no candidate score | Apache-2.0, 5,123,178,979 raw / 2.3B effective parameters. Native template renders, but mlx-lm 0.31.3 cannot load 60 K/V and K-norm tensors in layers 15–34. Hard stop before optimizer step, quantization, training, or judging. |
| 2026-07-12 | iteration 12 ft_v7-micro + wrapper-v4 | Qwen3-1.7B system | existing ft_v7_micro adapter + frozen red-flag directive | historical pre-versioned procedure: 147/200 deterministic, 67/200 category, 35/200 strict; blocked | Prefilter preserves all 30 ft_v2 and 16 prior-gain protects. Promotion still fails refusal 11→10, safety 14→12, and goal 1→0. No fusion or quantization. |
| 2026-07-12 | iteration 13 judge-protocol-v1 | unchanged ft_v2 and ft_v7-micro + wrapper-v4 answers | no training or generation | candidate A/B 87/83, agreement 164/200 (82%); ft_v2 A/B 165/67, agreement 76/200 (38%) | Measurement hard stop. Provenance/schema fixes work, but a structurally valid judge degenerates semantically. No ft_v2 adjudication, baseline re-pin, regression, promotion, or model artifact. Iteration 14 must qualify and pair blinded judges before suite access. |
| 2026-07-12 | iteration 14 judge-protocol-v2 | unchanged ft_v2 and ft_v7-micro + wrapper-v4 answers | no training or generation | measurement blocked; no trusted scorecard | Built perfect non-suite qualification, persistent blinded paired sessions, chained shards, hidden sentinels, evidence validation, anti-degeneracy checks, and per-system trust gates. Six paired attempts were quarantined before full trust; run 6 stopped at shard 1 on invalid sentinel evidence. No adjudication, baseline re-pin, regression, promotion, fusion, quantization, or serving change; ft_v2 remains pinned. |
| 2026-07-12 | iteration 15 owner-review-v1 | unchanged ft_v2 and ft_v7-micro + wrapper-v4 answers | no training or generation | `DO_NOT_PROMOTE`: difference 14/19 (16 required, 0 unsafe), gains 8/10, safety 18/18; preference baseline/candidate/tie 15/3/1 | Owner-declared instrument executed by the owner-delegated agent named in the immutable decision record. Five candidate defects and two sampled-gain failures confirmed. ft_v2 remains model of record, serving default, and recommended upload/run. |
| 2026-07-12 | iteration 16A ft_v8 + wrapper-v5 | Qwen3-1.7B | ft_v7_micro lineage + 30 scoped repairs; 1,120 rows, split 972/108/40 | `sf-gates-11`: 140/200 deterministic; prefilter reject | Unchanged 2,116-step r16 recipe, final train/valid 0.192/0.323, 15.55 GB peak. All 30 ft_v2 protects survive, but prior-gain protects `advs-v1-000012` and `ev1x-core2-000011` fail x1. No owner-review packet or promotion; ft_v2 remains serving default. |
