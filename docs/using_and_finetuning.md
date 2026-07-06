# Using SignalFit-SLM and fine-tuning it on your own data

A practical guide for anyone who wants to (a) run the model, (b) feed it their
own fitness data, or (c) retrain it on their own examples. Assumes a Mac with
Apple Silicon; everything runs locally, no API keys.

## 1. What this model is

A small (1.5B) fitness-coaching assistant that answers **only from a JSON
context** you give it. It has no memory, no account, no live data — the context
is its entire world. That design is what makes it trustworthy: every number it
may say is listed in the context's `allowed_numbers`, so hallucination is
machine-checkable.

```
your fitness data ──(adapter you write)──► sf-context-1 JSON ──► model ──► grounded answer
```

Input contract: `schemas/assistant_context.schema.json` (version `sf-context-1`).
Everything is nullable; list what's missing in `data_quality.missing_fields`.

## 2. Setup

```bash
git clone https://github.com/adidshaft/signalfit-slm && cd signalfit-slm
python3 -m venv .venv
.venv/bin/pip install jsonschema 'mlx-lm==0.31.3' 'transformers<5'
```

The base model (Qwen/Qwen2.5-1.5B-Instruct, ~3 GB) downloads from Hugging Face
on first use. LoRA adapters are not in the repo (weights are gitignored) —
train your own in ~10 minutes (§5) or run the base model without an adapter to
see the difference training makes.

Python 3.14 note: if `import mlx_lm` crashes in `tokenizer_utils.py`, wrap the
`AutoTokenizer.register("NewlineTokenizer", ...)` line in try/except — see
"Dependency reality check" in `docs/process_guide.md`.

## 3. Ask it questions

```bash
# against a context from the dataset
.venv/bin/python scripts/ask.py --random "should I train hard today?"
.venv/bin/python scripts/ask.py my_context.json "how is my sleep trending?"

# as an OpenAI-compatible local server
.venv/bin/python -m mlx_lm server --model Qwen/Qwen2.5-1.5B-Instruct \
  --adapter-path models/adapters/<your-run> --port 8080
```

## 4. Feed it YOUR data

Write a small adapter that maps your source (any tracker export, a CSV, manual
logs) into `sf-context-1`. Rules that matter:

1. **Generic field names only** (`recovery_score`, `hrv_ms`,
   `resting_heart_rate_bpm`, ...). Device-specific detail goes in
   `provenance.provider_metadata` only.
2. **Emit null, never omit** required leaves; list gaps in
   `data_quality.missing_fields`. The model is trained to say "I don't have
   that" — give it the chance.
3. **Build `allowed_numbers` mechanically**: walk your finished context and
   append every numeral as `{"value", "unit", "label"}` (see
   `collect_allowed_numbers` in `scripts/generate_seed_dataset.py`). Add any
   derived values you want the model to be able to cite (hours versions of
   minutes, etc.). If it's not in the list, the model isn't allowed to say it.
4. Set `provenance.hrv_method` (`rmssd` vs `sdnn`) and `strain_scale` honestly;
   don't silently rescale provider scores.
5. Validate before use:
   `.venv/bin/python scripts/validate_schema.py <dir-with-your-contexts>`
   (wrap each context in a minimal training-example envelope, or validate the
   context alone against `assistant_context.schema.json` with any JSON-Schema
   tool).

Real-data caveat (learned by testing on actual tracker exports): the current
model sometimes binds a real number to the wrong field (e.g. respiratory rate
quoted as resting HR) and invents derived comparisons. `scripts/ask.py` warns
on out-of-contract numbers, and the eval's `s3_field_binding` gate measures
this; §6 explains how to improve it with your own data.

## 5. Fine-tune on your own examples

Each training example is one JSON file (`schemas/training_example.schema.json`):
your context + the question + the *ideal* answer + labels. Study
`data/synthetic/curated/worked_examples/` for the exact shape.

The answer-writing rules that make the dataset work (full list in
`prompts/synthetic_data_generation.md`):
- every digit+unit in the answer must exist in `allowed_numbers` (±1.0);
- 60–160 words (30–80 for safety triage/refusals), ≤1 question, no brand names;
- lead with the recommendation, 1–3 data reasons, one concrete action;
- safety beats coaching: red flags → immediate care, zero training advice;
- moderate recovery → modified training, not reflexive rest.

Then the pipeline (identical to how this repo's datasets were built):

```bash
# 1. hard gates: schema + grounding + missing-fields consistency
.venv/bin/python scripts/validate_schema.py my_examples/

# 2. convert to chat JSONL + manifest
.venv/bin/python scripts/prepare_dataset.py my_examples/ -o data/ft_mine/all.jsonl

# 3. split (locked-eval isolation, persona-disjoint train/valid)
.venv/bin/python scripts/split_dataset.py data/ft_mine/all.jsonl --out-dir data/ft_mine

# 4. train — copy a config and point `data:` at data/ft_mine
cp training/configs/mlx_lora_qwen2.5-1.5b-ft_v2.yaml training/configs/mine.yaml
#    edit: data, adapter_path, iters (~2-2.5 epochs: iters ≈ 2.3 × train_count)
.venv/bin/python -m mlx_lm lora --config training/configs/mine.yaml

# 5. evaluate on the locked split you never trained on
.venv/bin/python scripts/generate_answers.py data/ft_mine/eval.jsonl \
  --adapter models/adapters/<your-run> -o /tmp/gens.jsonl
.venv/bin/python scripts/run_eval.py --examples my_examples/ \
  --generations /tmp/gens.jsonl --out-dir /tmp/report
```

Rules of thumb from this project's runs (details in `docs/process_guide.md`):
- 300–400 examples teach the answer *shape*; behaviors with <30 examples stay
  unreliable — when the eval finds a failure, fix it with **targeted** examples
  (we fixed safety with 100 aimed examples after 300 general ones didn't).
- Mark ~10% of examples `is_locked_eval: true` on personas that appear nowhere
  else, and never train on them — that's your honest scoreboard.
- Training takes ~10–20 min for 600–750 iterations on an M-series Mac
  (~10 GB peak RAM at batch 1, seq len 3072).

## 6. The improvement loop

When your model fails on real data: (1) make the failure a deterministic check
in `scripts/run_eval.py`; (2) calibrate it — all gold answers must pass, the
known failures must be caught; (3) generate examples that demonstrate the
correct behavior (plus benign hard-negatives so you don't overcorrect);
(4) retrain and compare runs on the same locked eval. That loop, run twice, is
the whole story of this repo — `docs/process_guide.md` § Step 7b.

## 7. Ship it (optional)

```bash
.venv/bin/python -m mlx_lm fuse --model Qwen/Qwen2.5-1.5B-Instruct \
  --adapter-path models/adapters/<your-run> --save-path models/fused/<your-run>
.venv/bin/python -m mlx_lm convert --hf-path models/fused/<your-run> \
  -q --q-bits 4 --q-group-size 64 --mlx-path models/export/<your-run>-4bit
```

The 4-bit folder (~0.9 GB) loads in MLX Swift (`MLXLLM`) on Apple Silicon
iPhones. Re-run the eval on the quantized model before shipping — quantization
can shift behavior.
