# Iteration 10 Qwen3.5-2B memory evidence

All runs used the retained 4-bit base at revision `15852e8c16360a2fea060d615a32b45270f8a8fc`, MLX 0.31.2, mlx-lm 0.31.3, batch size 1, gradient checkpointing, and `/usr/bin/time -l` on a 24 GB Mac.

The tokenizer-measured `ft_v7_micro` maximum is 2,249 tokens (`rel-v3-000063`). The 1,895-token probe is the longest train row retained by a lossless <=2,048-token subset (`agv4-000049`).

| log | rank/layers | tokens | outcome | host peak footprint |
|---|---:|---:|---|---:|
| `r16-l16-gc-max2249-smoke.log` | 16/16 | 450 sampled | step completed | 9.51 GB |
| `r16-l16-gc-max2249-worst-row-smoke.log` | 16/16 | 2,249 | Metal OOM | 23.90 GB |
| `r8-l8-gc-max2249-worst-row-smoke.log` | 8/8 | 2,249 | Metal OOM | 22.65 GB |
| `r4-l4-gc-max2249-worst-row-smoke.log` | 4/4 | 2,249 | Metal OOM | 21.80 GB |
| `r16-l16-gc-max1895-worst-row-smoke.log` | 16/16 | 1,895 | Metal OOM | 23.06 GB |
| `r4-l4-gc-max1895-worst-row-smoke.log` | 4/4 | 1,895 | Metal OOM | 21.21 GB |

The successful short step proves the software/training path works but is not a viable candidate. No full adapter was produced, and all diagnostic adapters/data were removed.
