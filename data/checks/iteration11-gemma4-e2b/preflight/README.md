# Iteration 11 Gemma 4 E2B preflight evidence

The exact repository `google/gemma-4-E2B-it` was pinned at revision
`9dbdf8a839e4e9e0eb56ed80cc8886661d3817cf`. Its per-repository Hugging Face
card metadata declares `apache-2.0`; the checked-in model card links the same
Apache 2.0 license. The single BF16 safetensors blob is 10,246,621,918 bytes
(Hub LFS SHA-256 `2db5482b20d746879bb3ef79b5203e9075a2e2b98f54ec7c2f281c1477ddc550`).

Safetensors header enumeration counts exactly 5,123,178,979 stored parameter
elements. The model card describes this size as 5.1B total including
per-layer embeddings and 2.3B effective parameters; “E2B” is an effective,
not raw, size label.

The unchanged `sf-chat-1` / `sft-sys-1` messages render correctly with the
repository tokenizer and native template. The rendered prompt contains the
native system turn, compact sorted `CONTEXT`, `QUESTION`, and model generation
turn. With `enable_thinking=false`, it contains no `<|think|>` trigger.

Actual mlx-lm support fails before generation. On MLX 0.31.2 / mlx-lm 0.31.3,
`mlx_lm.load()` rejects 60 checkpoint tensors absent from its constructed
model: `k_norm.weight`, `k_proj.weight`, and `v_proj.weight` for each language
layer 15 through 34. The exception is `ValueError: Received 60 parameters not
in model`. `/usr/bin/time -l` recorded 82,920,216 bytes peak footprint for the
failed load attempt; this is not an optimizer-step measurement.

Per the iteration-11 hard kill rule, the run stops at this support failure.
No direct answer, 2,249-token LoRA optimizer step, 4-bit conversion, full
training, suite generation, prefilter, judging, regression check, promotion,
fusion, or quantized re-evaluation was attempted. Null measurements in
`summary.json` are intentionally reported as not applicable rather than
estimated.
