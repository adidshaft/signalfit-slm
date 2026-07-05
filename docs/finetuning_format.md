# Fine-tuning Example Format (v0.1 — format id: sf-chat-1)

How a `training_example.schema.json` record becomes one chat-format JSONL line for
SFT (MLX `mlx_lm.lora` compatible; also fine for Unsloth/HF `trl`).

## JSONL line shape

```json
{"messages": [
  {"role": "system", "content": "<SYSTEM_PROMPT sft-sys-1>"},
  {"role": "user", "content": "CONTEXT:\n<context-json>\n\nQUESTION: <user_question>"},
  {"role": "assistant", "content": "<target_response.text>"}
]}
```

## System prompt (sft-sys-1 — fixed verbatim across ALL examples)

```
You are SignalFit, a fitness assistant. Answer ONLY from the CONTEXT JSON. If a
value is not in CONTEXT, say you don't have it — never estimate, never present
population numbers as the user's own. Hedge on estimate-grade or low-confidence
values. You are not a doctor and never diagnose; on medical red flags, stop
coaching and recommend appropriate care.
```

One fixed system prompt (not per-category) so inference needs no router; the model
learns task routing from the question + context. The prompt is versioned — any
wording change bumps `sft-sys-2` and invalidates score comparisons.

## Context serialization rules (applied by scripts/prepare_dataset.py)

1. Start from `example.context`, then **remove**:
   - `request.user_question` (it appears once, in the QUESTION line),
   - the whole `task` block (task category is a training LABEL, not a model input —
     at inference nothing classifies the question first).
2. Serialize compact (`separators=(",",":")`), keys sorted, UTF-8, no trailing
   whitespace. Determinism matters: the same example must always produce the same
   line (dataset hashing).
3. Everything else stays — including `allowed_numbers` (the grounding contract is
   part of the input the model must learn to respect) and `missing_fields`.

## What is NOT in the model input

`task_category`, `case_type`, `difficulty`, `target_response` labels
(`must_mention` etc.), `labels.*`, `generation.*` — these live only in the source
example for eval/analysis. The JSONL keeps a parallel `meta` is **not** emitted:
MLX treats extra keys as data. Instead `prepare_dataset.py` writes a sidecar
`<out>.manifest.json` mapping line number → example_id, task_category, case_type,
provider_mask, is_locked_eval, plus a SHA-256 of each line and of the whole file.

## Split policy (scripts/split_dataset.py)

- `is_locked_eval: true` → `eval.jsonl`, never anything else.
- Remainder: stratified by task_category → `train.jsonl` / `valid.jsonl`
  (default 90/10, seeded, deterministic; personas are NOT split across train and
  valid — split by persona_id first so valid measures generalization, not
  memorization of a persona's history).
- Output dir default `data/ft_v0/` with `manifest.json` (counts per category ×
  case_type, file SHA-256s, source example ids per split). CI/train scripts must
  refuse to run if train ∩ eval ids ≠ ∅.

## Version pinning

A dataset release = (schema_version sf-context-1, format sf-chat-1, system prompt
sft-sys-1, generator prompt_versions, split seed). All five recorded in the
manifest; models/README.md run log references the manifest hash.
