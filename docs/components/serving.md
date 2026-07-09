# Serving & Shipping — using the model

## Ask it something — `scripts/ask.py`

One-command interface to the current adapter (defaults to ft_v2, the model of
record):

```bash
.venv/bin/python scripts/ask.py <context-or-example.json> "should I train hard today?"
.venv/bin/python scripts/ask.py --random "how did I sleep?"   # random curated context
```

Accepts a bare `sf-context-1` JSON or a full training example (context
extracted). After generating, it runs the grounding regex **on the fly** and
prints a warning for any number outside the context's `allowed_numbers` — the
same contract as training and eval, enforced at chat time.

## Batch generation — `scripts/generate_answers.py`

Two modes, both writing `{"example_id", "answer"}` lines for `run_eval.py`:

- **split mode**: a prepared `eval.jsonl` + its sidecar manifest (drops the
  gold assistant turn, prompts with system+user);
- **`--examples` mode**: directories of training-example JSONs (e.g. the
  frozen suite slices) — the prompt is built exactly as `prepare_dataset.py`
  builds training input, so eval-time prompting can never drift from training.

Requires `mlx-lm`; import-guarded so the rest of the pipeline works without it.
~20 s/answer for the 1.5B model on an M-series Mac.

## Shipping to iOS

```bash
.venv/bin/python -m mlx_lm fuse --model Qwen/Qwen2.5-1.5B-Instruct \
    --adapter-path models/adapters/<run> --save-path models/fused/<run>
.venv/bin/python -m mlx_lm convert --hf-path models/fused/<run> \
    -q --q-bits 4 --q-group-size 64 --mlx-path models/export/<run>-4bit
```

The 4-bit folder (~0.9 GB) loads in MLX Swift (`MLXLLM`) on Apple-Silicon
iPhones. The app-side contract: the app builds the `sf-context-1` JSON
(adapter from provider data), sends `CONTEXT + QUESTION` with the pinned
system prompt, and runs the same on-device grounding check on the output.

**Rule:** re-run the eval suite on the *quantized* model before shipping —
quantization can shift behavior, and only the frozen suite can say by how
much. `models/fused/`, `models/export/`, and `models/adapters/` are gitignored
(artifacts, not source); the HF-upload path for sharing adapters is
`HF_UPLOAD.md` at the repo root.
