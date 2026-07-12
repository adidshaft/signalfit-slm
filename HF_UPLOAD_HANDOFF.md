# Handoff: publish the SignalFit-SLM model to Hugging Face

You are picking up a finished model and shipping it to the Hugging Face Hub.
The model is trained, promoted, 4-bit quantized, and safety-verified. Your job
is packaging and upload only — **do not retrain, re-quantize, or change any
gate, adapter, or eval artifact.**

## What you are shipping

- **Artifact:** `data/checks/ship-ft_v10/export-4bit/` — a standalone MLX
  4-bit quantized model (`qwen3` architecture, 4 bits, group size 64, affine),
  ~934 MB. It already contains `config.json`, `model.safetensors`,
  `model.safetensors.index.json`, `tokenizer.json`, `tokenizer_config.json`,
  `chat_template.jinja`, `generation_config.json`.
- **Base model:** `Qwen/Qwen3-1.7B` (Apache-2.0).
- **Fine-tune:** LoRA adapter `models/adapters/ft_v10_qwen3-1.7b` fused into the
  base, then quantized. Adapter and fused fp16 model are in the repo if the card
  needs to reference them.
- **Serving wrapper:** the model is designed to run behind
  `scripts/answer_with_check.py` (system label `answer-check-v7`), which adds
  grounding/safety retries. The wrapper is not part of the uploaded weights but
  MUST be described in the model card, because the safety numbers below are
  measured *with* it.

## Verified evaluation (do not re-run to "improve" — just report these)

Scored on the frozen 200-case suite `eval/v1` at gate version `sf-gates-13`,
model served behind `answer-check-v7`:

- Safety gates: **s1 (no coaching in triage) 18/18**, **s2 (no protocol in
  refusal) 19/19**, **s3 (field binding) 196/200**.
- Deterministic pass rate: **0.68 (135/200)**.
- Promoted under a **safety-based promotion bar** (zero safety-gate regression;
  quality-gate edge cases tolerated as documented known limitations). Full
  rationale: `docs/PROMOTION_DECISION_ft_v10.md`.
- Known limitations (quality-gate, not safety): `agen-v1-000135` (refusal
  slightly over the length ceiling), `advs-v1-000007` (arithmetic wording in an
  otherwise-correct triage).

## Steps

1. **Pick the repo id** with the owner (e.g. `<owner>/signalfit-slm-1.7b-4bit`).
   Confirm license tag `apache-2.0` (inherited from Qwen3-1.7B).

2. **Write the model card** (`README.md` inside the uploaded repo). The repo's
   top-level `README.md` is the source of truth for description, intended use,
   the serving-wrapper requirement, the safety numbers above, limitations, and
   the safety position — adapt it into a proper HF card with YAML frontmatter:
   ```yaml
   license: apache-2.0
   base_model: Qwen/Qwen3-1.7B
   library_name: mlx
   pipeline_tag: text-generation
   tags: [mlx, lora, qwen3, health, fitness, wearable-data, synthetic-data, on-device]
   ```
   The card MUST state: (a) this is a grounded, on-device fitness-data
   assistant, not a medical device; (b) it is meant to run behind the
   `answer-check-v7` grounding/safety wrapper; (c) the safety and grounding
   design (refuses to coach on medical red flags, never invents numbers).

3. **Upload the quantized folder** with the HF CLI (the person running this must
   `huggingface-cli login` first — it is an interactive credential step you
   cannot do headless):
   ```bash
   huggingface-cli upload <owner>/signalfit-slm-1.7b-4bit \
     data/checks/ship-ft_v10/export-4bit . \
     --repo-type model
   ```
   Verify the uploaded file list matches the local `export-4bit/` contents and
   that `model.safetensors` transferred fully (~934 MB).

4. **Smoke-test the published model** by loading it back with MLX and running
   one generation, to confirm the upload is intact:
   ```bash
   .venv/bin/python -c "from mlx_lm import load, generate; m,t=load('<owner>/signalfit-slm-1.7b-4bit'); print(generate(m,t,prompt=t.apply_chat_template([{'role':'user','content':'hi'}],add_generation_prompt=True),max_tokens=20))"
   ```

## Rails

- Do not commit HF-specific config files (`.gitattributes`, `.hfignore`,
  `requirements.txt`, or an HF-only `HF_UPLOAD.md`) back into this repo.
- Do not modify anything under `eval/v1/` (frozen suite), `models/adapters/`,
  or `data/checks/ship-ft_v10/` — those are the verified artifacts.
- Keep `scripts/answer_with_check.py` and the gate scripts unchanged; the safety
  numbers depend on them exactly as they are.
- If the model card needs numbers, take them from
  `data/checks/ship-ft_v10/SHIP_VERDICT.md` and
  `docs/PROMOTION_DECISION_ft_v10.md` — do not recompute or round.
