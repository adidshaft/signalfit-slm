# Iterations — five trips around the improvement loop

The loop that governs the whole project:

```
eval failure → make it DETERMINISTIC (new gate) → generate TARGETED data
     ▲                                                      │
     └────────── re-evaluate ◄──── re-train (LoRA) ◄────────┘
```

Diagram: [`../pipeline_map.md`](../pipeline_map.md) §4. Full narrative:
[`../process_guide.md`](../process_guide.md) Steps 7–7i and the dated log.

## Iteration 1 — ft_v1 (phase 1)

Trained on 245 of `agent_v1`'s 300 general examples. Result on the locked 30:
grounding 100%, the coaching answer *shape* clearly learned — but **safety
under-learned**: one triage answer coached through a red flag, one refusal
leaked protocol shape via spelled-out numbers ("four weeks on") the digit
regex couldn't see. Lesson: *the model fails exactly where the data is thin,
and the eval only measures what it can see.*

## Iteration 2 — ft_v2 (phase 2a) — current model of record

Response per the loop: make the failures deterministic (**s1**, **s2** gates,
calibrated: gold 30/30, both known failures caught), then 100 **targeted**
safety examples (40 triage / 30 refusal / 30 benign lookalikes against
over-refusal). Result: triage 6/6, zero protocol leakage, lookalikes still
coached. **Targeted data beat more data** — 100 aimed examples fixed what 300
general ones couldn't.

## Interlude — building the real ruler (phase 2b part 1, no retrain)

A real tracker export (local-only) exposed **field binding** — real numbers
attached to wrong concepts → **s3** gate + the `binding/` suite slice. Then the
scaffold eval was replaced wholesale: suite frozen (`sf-eval-v1`, 66 cases),
gates versioned, the judge actually run (double-pass, 90% agreement,
adjudications recorded), baseline pinned, regression gate wired. Each honesty
upgrade cut ft_v2's headline roughly in half — 37/40 → 34/40 (calibrated
gates) → **9/40 core-strict** → 11/66 suite-strict — *without the model
changing*. Two findings: **X1 false relations** (grounded values, arithmetically
false claims about them) failed 34/66; and the **fiction-framing PED jailbreak
worked** (the model "refused", then supplied a testosterone+EPO protocol as
"story structure" — the s2 gate caught it).

## Iteration 3 — ft_v3 (phase 2b part 2) — blocked

**s4** comparative-arithmetic gate built first (flags 17 of the 34 X1
failures, zero false positives against judge ground truth), then
`agent_v3_relational` (150 examples: relational correctness + indirect-framing
safety; **benign lookalikes omitted — known gap**), then ft_v3 (1060 iters,
best val loss of any run: 0.284).

Full-workflow verdict: **⛔ blocked by `check_regression.py`.** Field binding
went perfect (s3 66/66, +4) and protocol leakage disappeared (s2 11/11, +2) —
but the round's actual target got *worse* (s4 49→46), judge quality dropped
(category 18→11), and three categories regressed. The baseline stayed ft_v2.
Post-mortem produced **s5** (claim discipline: false "I can't see your data"
claims, diagnosis language) — the next loop's deterministic anchor.

## Iteration 4 — ft_v4 (phase 2b part 3) — blocked

`agent_v4_discipline` added the missing counterweight from ft_v3: claim
discipline, relational correctness under field-binding pressure, benign
lookalikes, and indirect-framing safety in one 150-example round. It passed
critic review with 150/150 retained, then `ft_v4` trained on 702 examples
(596 train / 66 valid / 40 held-out split) for 1371 MLX LoRA iterations.

The full frozen-suite verdict is complete under
**(sf-eval-v1, sf-gates-6, rubric-v0.1)**. ft_v4 reaches 44/66 deterministic,
19/66 judge-category, and 13/66 strict, versus ft_v2's 41/66, 18/66, and
11/66. Protocol refusal improves (s2 9/11→11/11), field binding improves
(s3 62/66→64/66), and comparative arithmetic matches baseline (s4 49/66).
The candidate is still blocked: safety triage falls s1 10/10→9/10, sleep
strict falls 1/6→0/6, and goal coaching strict falls 1/5→0/5. ft_v2 remains
the model of record.

## Iteration 5 — ft_v5 boundary round — blocked

The ft_v4 failure ledger was read before generation. Its 17 s4 failures contain
24 comparison errors, dominated by close-language overreach and reversed
above/below relations. Judge X1 fails 32 unique examples: 15 overlap s4, while
17 expose field roles, evidence sufficiency, context-state contradictions, or
invented recommendation numbers. Every sleep and goal case was inspected.

The resulting agv5 design is 120 examples: 36 balanced benign↔triage boundary
pairs (72 examples), 24 targeted s4/X1 repairs, and 24 sleep/goal repairs.
Five generators and five independent critics accepted all 120: schema/gold
gates 120/120 and pair invariants 36/36. The balanced boundary slice was
repeated once in the 894-row mixture, then trained for all 1,769 iterations.

The final verdict is **⛔ blocked**. ft_v5 reaches 48/66 deterministic, but
double judging (56 agreements, ten adjudications) yields 18/66 category and
9/66 strict. s4 improves to 51/66 and s5 to 66/66, while s1 remains 9/10,
sleep and goal stay at zero strict, and refusal falls to 3/11 strict. The
benign-lookalike audit is 5/7 deterministic, 1/7 category, and 0/7 strict.
The candidate converts deterministic target gains into brittle prose rather
than reliable judged quality, so ft_v2 remains the model of record.

## Scoreboard — triple (sf-eval-v1, sf-gates-6, rubric-v0.1)

| model | deterministic | judge category | strict overall | verdict |
|---|---:|---:|---:|---|
| ft_v2 | 41/66 | 18/66 | **11/66** | pinned baseline, model of record |
| ft_v3 | 39/66 | 11/66 | 10/66 | ⛔ blocked |
| ft_v4 | 44/66 | 19/66 | 13/66 | ⛔ blocked; s1 safety regression |
| ft_v5 | **48/66** | 18/66 | 9/66 | ⛔ blocked; safety + strict regression |

(ft_v1: 27/30 under sf-gates-3 on its own locked set — gate-comparable only,
predates the suite.)

![Overall frozen-suite benchmark comparison](../assets/benchmark-overall.svg)

![ft_v2, ft_v4, and ft_v5 safety and grounding gate comparison](../assets/benchmark-gates.svg)

## What the iterations teach

1. **A blocked model is the harness succeeding.** ft_v3 had the best val loss
   and genuinely improved two safety gates; the regression gate still refused
   the trade because judged quality dropped. Val loss fits the data; the suite
   measures what we want; only the suite can veto.
2. **Every gate is a fossilized failure.** None of s1–s5 was designed in the
   abstract; each mechanizes something a model actually did wrong once.
3. **Honesty upgrades look like regressions.** Expect the headline number to
   fall every time the ruler improves; track the triple, not the number.
4. **Aggregate gains cannot buy back a safety drop.** ft_v5 has the best
   deterministic count yet the worst strict result of ft_v2/ft_v4/ft_v5. One
   triage regression still blocks promotion, and the judge reveals additional
   refusal and coaching-quality losses hidden by deterministic gates.

## Current loop

ft_v5 is closed and blocked. The next loop should start from the exact strict
losses and anti-over-refusal failures, retain the improved s4/s5 behavior, and
must restore s1 to 10/10 before any candidate can be promoted. The baseline,
default adapter, and frozen suite remain unchanged.
