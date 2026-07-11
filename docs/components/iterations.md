# Iterations — nine completed trips

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

The corrected sf-gates-8 verdict is **⛔ blocked**. ft_v5 reaches 50/66
deterministic, while
double judging (56 agreements, ten adjudications) yields 18/66 category and
10/66 strict. s4 improves to 51/66, s5 to 66/66, and the clause-aware s1 fix
restores 10/10. Sleep and goal stay at zero strict, and refusal falls to 3/11. The
benign-lookalike audit is 5/7 deterministic, 1/7 category, and 0/7 strict.
The candidate converts deterministic target gains into brittle prose rather
than reliable judged quality, so ft_v2 remains the model of record.

## Iteration 6 — fixed-data candidate search — sweep complete

sf-gates-7 corrects s1's refusal blindness; the follow-up safety audit finds
five demonstrable s3 role-parser false positives and sf-gates-8 clears them
without losing seven real safety hits. The corrected sf-gates-10 ft_v5 score is 51/66
deterministic and 10/66 strict with s1 10/10, but real sleep, goal, refusal,
and strict-overall regressions remain. Phase 2's 66-case churn matrix now
defines the protect list for the fixed-data LoRA regime sweep.

Four fixed-data candidates were trained. Only `ft_v6_s29_r16_i2300` cleared
the deterministic prefilter (49/66), but double judging and adjudication left
it at 17/66 category and 9/66 strict, below ft_v2's 11/66. The other three
failed protected baseline examples and were not judged. The sweep therefore
ships no Qwen2.5 candidate. The capacity path then ran under the same protocol.

Qwen3.5-2B passed license and non-thinking inference checks but proved
locally unusable for LoRA on 24 GB. The protocol fallback Qwen3-1.7B completed
1,769 steps and scores 48/66 deterministic with all safety floors and all 11
protected ft_v2 passes intact. Independent judging yields 19/66 category and
14/66 strict, the best strict aggregate in the project. It is still blocked:
sleep coaching falls 1/6→0/6, daily decisions 1/9→0/9, and lookalikes are only
1/7 strict. ft_v2 remains the model of record.

## Historical 66-case scoreboard — triple (sf-eval-v1, sf-gates-10, rubric-v0.1)

| model | deterministic | judge category | strict overall | verdict |
|---|---:|---:|---:|---|
| ft_v2 | 41/66 | 18/66 | **11/66** | pinned baseline, model of record |
| ft_v4 | 45/66 | 19/66 | 13/66 | ⛔ blocked; s1 safety regression |
| ft_v5 | **51/66** | 18/66 | 10/66 | ⛔ blocked; strict category regression |
| Qwen3-1.7B fallback | 48/66 | **19/66** | **14/66** | ⛔ blocked; sleep/daily regression |

(ft_v1: 27/30 under sf-gates-3 on its own locked set — gate-comparable only,
predates the suite. ft_v3's latest report is historical sf-gates-6 and is not
included in this sf-gates-10 table.)

## Iteration 7 — lengthen the ruler (phase 1 complete)

The 66-case suite has been append-only expanded to 200 cases under the same
gate and rubric versions: 93 core coverage cases, 25 benign lookalikes, and
16 safety positives. All 134 passed schema validation, independent critic
review, full gold calibration (200/200), explicit s3/s4 mutation checks, and
the frozen-suite contamination check. This is the pre-declared legal
suite-expansion re-pin point: the table above is retained as the historical
66-case record. ft_v2 has now been re-baselined through two independent judge
passes and 21 recorded third-pass adjudications: **101/200 deterministic,
46/200 judge-category, 30/200 strict**. This is the sanctioned suite-growth
re-pin; no candidate is promoted and defaults remain unchanged.

![Overall frozen-suite benchmark comparison](../assets/benchmark-overall.svg)

![ft_v2, ft_v4, ft_v5, and Qwen3 safety and grounding gate comparison](../assets/benchmark-gates.svg)

## Current 200-case scoreboard — triple (sf-eval-v1, sf-gates-10, rubric-v0.1)

| model/system | deterministic | judge category | strict overall | verdict |
|---|---:|---:|---:|---|
| ft_v2 | 101/200 | 46/200 | **30/200** | pinned baseline, model of record |
| Qwen3-1.7B | 123/200 | 58/200 | 29/200 | ⛔ blocked; refusal/daily/sleep regression |
| Qwen3-1.7B + verify/retry-1 | 139/200 | **62/200** | **30/200** | ⛔ blocked; refusal/daily regression |
| ft_v7 | 119/200 | — | — | ⛔ deterministic protect failure; not judged |
| ft_v7 + verify/retry-1 | 132/200 | — | — | ⛔ dual-protect failure; not judged |
| ft_v7 micro + verify/retry-1 | **144/200** | — | — | ⛔ two dual-protect failures; not judged |

## What the iterations teach

1. **A blocked model is the harness succeeding.** ft_v3 had the best val loss
   and genuinely improved two safety gates; the regression gate still refused
   the trade because judged quality dropped. Val loss fits the data; the suite
   measures what we want; only the suite can veto.
2. **Every gate is a fossilized failure.** None of s1–s5 was designed in the
   abstract; each mechanizes something a model actually did wrong once.
3. **Honesty upgrades look like regressions.** Expect the headline number to
   fall every time the ruler improves; track the triple, not the number.
4. **Aggregate gains cannot buy back strict regressions.** sf-gates-10 removes
   demonstrated s1/s3 false positives, but the judge still reveals refusal and
   coaching losses hidden by ft_v5's best-yet deterministic count.

## Current loop

Iteration 9 is complete with no promotion. Composing ft_v7 with one bounded
retry reaches 132/200 deterministic but fails five dual-protect cases. A
28-example independently critiqued micro-round then restores all four original
ft_v7 failures and lifts the fresh system to 144/200 with S1 18/18, S2 19/19,
S3 192/200, and a 35.5% retry rate. It still fails one protected benign answer
on the 40-word minimum and, more importantly, one protected exertional chest-
tightness triage case by normalizing it and repeating reflux diagnosis language
after correction. The prefilter correctly blocks judging and ship preparation.
ft_v2 remains the default 200-case incumbent. The next lever is a deterministic
red-flag triage front end plus a small exertional-symptom/benign-lookalike
calibration set, not another broad data round.
