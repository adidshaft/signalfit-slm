# Component Index — every moving part of SignalFit-SLM

This folder documents **every component** in the system, grouped into six
files. The visual companion is [`../pipeline_map.md`](../pipeline_map.md)
(four Mermaid diagrams of the same material); the narrative of *why* each
piece was built when it was is [`../process_guide.md`](../process_guide.md).

| File | Covers |
|---|---|
| [contracts.md](contracts.md) | Everything decided *before* training: schemas (`sf-context-1`, `sf-train-1`, `sf-chat-1`), the `allowed_numbers` grounding contract, safety policy, judge rubrics, eval plan, persona library, the Atria reference |
| [data-factory.md](data-factory.md) | How training examples get made: the deterministic context sampler, generator/critic subagents, the validator hard-gate, all data rounds (`seed_v0`, `agent_v1`, `agent_v2_safety`, `agent_v3_relational`, `agent_v4_discipline`), real-world data rules, the parked teacher-API path |
| [dataset-and-training.md](dataset-and-training.md) | Example JSON → chat JSONL → splits → LoRA: `prepare_dataset`, `split_dataset`, manifests, `data/ft_v0…v4`, base-model/license choice, MLX configs, adapters ft_v1/v2/v3/v4 |
| [eval-harness.md](eval-harness.md) | The scoring machine: frozen suite `eval/v1` (core/adversarial/binding), `freeze_eval`, gold calibration, gates x1…s5 with `GATE_VERSION`, double-pass LLM judging, adjudication, `apply_judge`, pinned baseline, `check_regression` |
| [serving.md](serving.md) | Using and shipping the model: `ask.py`, `generate_answers.py`, fuse → 4-bit quantize → iOS via MLX Swift |
| [iterations.md](iterations.md) | The improvement loop: ft_v1 → ft_v2 → ft_v3 (blocked) → ft_v4 (judging), what each found, the current scoreboard |

## The three ideas that hold everything together

1. **Grounding is machine-checkable.** The model answers only from a JSON
   context, and every number it may cite is enumerated in
   `context.allowed_numbers`. A regex can therefore *prove* an answer cites
   nothing outside its contract — on training data before it enters, and on
   model output at eval time.
2. **Numbers are deterministic; only language comes from a model.** Contexts
   are simulated from a coherent 30-day series (so "your 30-day average" is
   the true mean). Generator agents write only the words around those numbers,
   and a validator rejects anything ungrounded.
3. **A score is a triple.** Every score is meaningful only as
   **(eval suite, gate version, rubric version)** — currently
   (`sf-eval-v1`, `sf-gates-6`, `rubric-v0.1`). The regression gate refuses to
   compare across mismatched triples, so numbers can't silently drift.
