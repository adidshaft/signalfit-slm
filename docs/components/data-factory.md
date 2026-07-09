# Data Factory — how a training example comes to exist

Core principle: **numbers are deterministic, only language comes from a
model.** No paid APIs anywhere — generation is done by agent sessions with
file access, a validator they run themselves, and a critic pass.

## The context sampler (deterministic numbers)

| Component | Job |
|---|---|
| Simulated 30-day physiology series | Coherence by construction: "your 30-day average HRV" is the *true mean* of an actual generated series, trends are real trends of it, anomalies are planted deliberately. |
| `scripts/make_context_specs.py` | Turns the simulator into chunked, reproducible **context specs** (10 chunks × 30) covering the planned distribution: task categories, case types (normal / edge / safety / lookalike), provider masks (`wearable_full`, `ring_no_strain`, manual-only, …), difficulty 1–3. |
| `scripts/generate_seed_dataset.py` | The template engine behind `seed_v0` — 30 template examples (3 per category) used to smoke-test the whole pipeline before scaling. **Rule: never scale before the 30-example version passes every gate.** |

## The agent assembly line (language)

```
context specs ─→ GENERATOR subagent ─→ validate_schema.py ─→ CRITIC subagent ─→ curated/
                 (writes question,      HARD GATE: schema     (qualitative:      committed
                  answer, labels;       validity + grounding   brands, budget,    per chunk
                  runs the validator    + missing-fields       anti-conservatism,
                  itself, fixes)        consistency; exit      safety precedence;
                                        non-zero = reject)     fix or reject)
```

- **Generator prompts** live in `prompts/synthetic_data_generation.md` (and
  the safety variant used for round 2); they embed the safety policy and the
  **anti-conservatism rule**: recovery 34–66 on a normal case → conditional /
  modified training, *not* reflexive rest — this is how the model avoids
  learning overcaution.
- **`scripts/validate_schema.py`** is the hard gate (also used standalone and
  in CI style): JSON-Schema validity of both example and context, the
  grounding regex on the gold text, and `missing_fields` ↔ actually-null
  cross-checks (`MISSING_FIELD_PATHS`).
- **Critic prompts** (`prompts/synthetic_data_critic.md`) review against the
  judge rubrics *before* an example is accepted.
- Every round writes a **generation report** (per-chunk yield, rejects,
  failure modes) next to its raw output.

## The data rounds (each aimed at a measured failure)

| Round | Size & mix | Aimed at | Outcome |
|---|---|---|---|
| `seed_v0` + `worked_examples` | 30 templates + 2 hand-written | pipeline smoke test | all gates green; trained ft_v0/ft_v1 heritage |
| `agent_v1` | 300 general, 10 categories | first real model (ft_v1) | answer *shape* learned; safety under-learned |
| `agent_v2_safety` | 100 = 40 triage / 30 refusal / **30 benign lookalikes** | ft_v1's two safety failures | both eliminated in ft_v2; zero over-refusal — *targeted data beat more data* |
| `agent_v3_relational` | 150 = 110 answer / 30 refuse / 10 triage, 6 chunks | X1 false relations + indirect-framing safety | ft_v3 **blocked** by regression gate; lookalikes were omitted (known gap) — see [iterations.md](iterations.md) |
| `agent_v4_discipline` | 150 = claim discipline / relational pressure / benign lookalikes / indirect safety, 6 chunks | ft_v3 post-mortem: unsupported labels, false missing-data claims, lookalike gap | critic-passed 150/150; ft_v4 scored 44/66 deterministic, 19/66 judge-category, 13/66 strict; blocked by s1 safety regression |

All curated examples live in `data/synthetic/curated/<round>/`, one JSON per
example, committed in chunks of ~25 so session interruptions never lose work.

## Real-world data (`data/real_world/`)

Local-only by design — the directory's `.gitignore` keeps every export out of
git. Rules: never copy real values into synthetic examples or docs; never
relax the ignore; delete exports when done. What a real-data failure
contributes to the committed repo is its **shape**, rebuilt with synthetic
values — that is exactly what the eval suite's `binding/` slice is.

## The parked teacher path

`scripts/generate_teacher_batch.py` — the original plan to have a frontier
model write the ~3.5k dataset via the paid Batch API (structured outputs,
grounding re-check on collect, ~$45 for 3.5k). Built and dry-run verified,
then **descoped** in favor of the zero-cost agent factory above. Kept in the
repo as the escape hatch if generation ever needs to scale beyond what agent
sessions can produce.
