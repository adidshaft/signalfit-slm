---
license: apache-2.0
base_model: Qwen/Qwen3-1.7B
library_name: mlx
pipeline_tag: text-generation
tags:
  - mlx
  - lora
  - qwen3
  - health
  - fitness
  - wearable-data
  - synthetic-data
  - on-device
model-index:
  - name: SignalFit-SLM ft_v10 (Qwen3-1.7B LoRA, 4-bit)
    results:
      - task:
          type: text-generation
          name: Grounded fitness coaching
        dataset:
          name: SignalFit-SLM frozen suite v1
          type: synthetic
        metrics:
          - type: safety_s1_no_coaching_in_triage
            value: 1.000
            name: s1 no coaching in triage (18/18)
          - type: safety_s2_no_protocol_in_refusal
            value: 1.000
            name: s2 no protocol in refusal (19/19)
          - type: safety_s3_field_binding
            value: 0.980
            name: s3 field binding (196/200)
          - type: deterministic_pass_rate
            value: 0.680
            name: Deterministic pass rate (135/200)
---

# SignalFit-SLM

A small, on-device assistant for **wearable fitness data**. It reads a
structured context object (your recovery, HRV, sleep, workouts) and a question,
and returns a grounded answer — using only the numbers in front of it, refusing
to coach on medical red flags, and never inventing data.

The model is a LoRA fine-tune of **Qwen3-1.7B** (Apache-2.0), served behind a
deterministic grounding/safety wrapper, and shipped as a **4-bit quantized
~934 MB build** that runs on a phone via MLX.

---

## Current status: shipped ✅

**Model of record: `ft_v10_qwen3-1.7b` + `answer-check-v7` wrapper** (promoted
2026-07-13). Shippable on-device artifact:
`data/checks/ship-ft_v10/export-4bit/` (4-bit, ~934 MB).

Verified on the frozen 200-case suite (`eval/v1`) at gate version
`sf-gates-13`, served behind the wrapper:

| Gate | Result | |
|---|---|---|
| s1 — no coaching in triage | **18/18** | safety |
| s2 — no protocol in refusal | **19/19** | safety |
| s3 — field binding | **196/200** | safety |
| deterministic pass rate | 135/200 | quality |

Promoted under a **safety-based bar**: zero safety-gate regression required;
quality-gate edge cases (arithmetic wording, length) are tracked as known
limitations, not hidden. Full rationale and the two known limitations are in
[`docs/PROMOTION_DECISION_ft_v10.md`](docs/PROMOTION_DECISION_ft_v10.md).

**→ To test it, see [`docs/testing_guide.md`](docs/testing_guide.md).**
**→ To publish it to Hugging Face, see [`HF_UPLOAD_HANDOFF.md`](HF_UPLOAD_HANDOFF.md).**

---

## Quickstart — ask the model one question

```bash
.venv/bin/python scripts/answer_with_check.py \
  --context examples/sample_context.json \
  --expected-action answer_with_caveat \
  --model data/checks/ship-ft_v10/export-4bit \
  -o /tmp/answer.jsonl

python3 -c "import json;print(json.loads(open('/tmp/answer.jsonl').readline())['answer'])"
```

`examples/sample_context.json` is a ready-to-edit context. Swap in your own
numbers and question — but keep `context.allowed_numbers` in sync (it lists
every value the model is allowed to cite). Details in the testing guide.

---

## How it works

- **Context-bound.** The model has no live access to your accounts or devices.
  Every answer depends only on the context object you pass in. Providers
  (WHOOP, Apple Health, Garmin, Oura, Fitbit, Ultrahuman, manual logs) are
  supported by first mapping their exports into the shared context schema
  (`schemas/assistant_context.schema.json`).
- **Grounded by construction.** A deterministic evaluator (`scripts/run_eval.py`,
  gate version `sf-gates-13`) encodes every safety and grounding rule as a
  fossilized past failure: numbers must come from `allowed_numbers`, metrics
  must bind to the right field, triage cases must not be coached, refusals must
  not describe protocols.
- **Wrapped for serving.** `scripts/answer_with_check.py` (`answer-check-v7`)
  wraps the model: it checks each draft against those gates and issues bounded,
  echo-safe corrective retries. The safety numbers above are measured *with*
  this wrapper — it is part of the product, not an afterthought.
- **Evaluated against a frozen suite.** `eval/v1` is a 200-case immutable suite
  (sha256-manifested, contamination-guarded). Candidates are compared to the
  pinned `ft_v2` baseline via `scripts/check_sweep_candidate.py`; scores are
  only comparable within one gate version.

## The journey (19 iterations)

The project spent most of its life with `ft_v2` (Qwen2.5-1.5B) as model of
record because no candidate could clear the promotion bar. The breakthrough
came from correctly diagnosing *why* candidates kept failing:

- The recurring **sleep-arithmetic failure was a training-data coverage gap** —
  the eval tested sleep `debt`/`need`/`efficiency` fields that appeared in zero
  training examples. Adding them fixed it.
- A **refusal-length failure was seed noise**; a **refusal-softening failure**
  was a behavior gap fixed by crisp refusal examples.
- The remaining protect-churn (each retrain fixes its targets and regresses ~2
  different quality cases) proved **irreducible at 1.7B**, which is why the
  promotion bar was changed to be safety-based rather than perfectionist.
- The final apparent "safety regression" in the quantized model was a **gate
  false positive** on a curly apostrophe in a safe refusal, fixed as
  `sf-gates-13` — the gate, not the model.

The full dated history is in [`docs/process_guide.md`](docs/process_guide.md);
the component map is in [`docs/pipeline_map.md`](docs/pipeline_map.md). The
detailed stage log, naming conventions, per-iteration benchmark numbers, and
the full adapter table are archived in
[`docs/project_history.md`](docs/project_history.md).

## Repository layout

| Path | Purpose |
|---|---|
| `docs/` | Product brief, schema, safety policy, eval plan, process guide, promotion procedure, testing guide |
| `schemas/` | JSON Schemas for assistant context and training examples |
| `prompts/` | Generation, critique, and eval-case prompts |
| `data/synthetic/curated/` | Curated training rounds (`agent_v1` … `agent_v10_micro`) |
| `data/ft_v10_qwen3_1.7b/` | The training dataset for the shipped model |
| `eval/v1/` | Frozen 200-case suite + pinned `ft_v2` baseline (immutable) |
| `models/adapters/ft_v10_qwen3-1.7b/` | The shipped LoRA adapter |
| `data/checks/ship-ft_v10/export-4bit/` | **The shippable 4-bit on-device model** |
| `scripts/` | Eval gates, serving wrapper, dataset prep, prefilter, ship verification |
| `training/configs/` | MLX LoRA training configs |

## Safety position

The assistant supports fitness decisions; it does not replace medical care. It
refuses unsafe requests, avoids diagnosis, flags missing context, and
recommends real-world care for urgent symptoms. On a medical red flag it stops
coaching entirely. See [`docs/safety_policy.md`](docs/safety_policy.md).

**This is not a medical device.** It is not a store for real user health
exports (`data/real_world/` is a local-only placeholder), and it is not
provider-specific software.

## Reproduce / extend

1. Map provider exports into `schemas/assistant_context.schema.json` and
   validate with `scripts/validate_schema.py`.
2. Prepare/split datasets with `scripts/prepare_dataset.py` and
   `scripts/split_dataset.py`.
3. Train with a config under `training/configs/` (MLX LoRA).
4. Evaluate on the frozen suite; a candidate ships only after
   `scripts/ship_verify.sh` returns `SHIP_OK` on its 4-bit quantized build.

See [`docs/promotion_procedure.md`](docs/promotion_procedure.md) for the exact
gate sequence a new candidate must pass.

## Contact

Maintainer: [@adidshaft](https://x.com/adidshaft)
