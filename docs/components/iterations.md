# Iterations — sixteen completed trips

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

## Historical 200-case scoreboard — pre-versioned judge procedure

| model/system | deterministic | judge category | strict overall | verdict |
|---|---:|---:|---:|---|
| ft_v2 | 101/200 | 46/200 | **30/200** | pinned baseline, model of record |
| Qwen3-1.7B | 123/200 | 58/200 | 29/200 | ⛔ blocked; refusal/daily/sleep regression |
| Qwen3-1.7B + verify/retry-1 | 139/200 | **62/200** | **30/200** | ⛔ blocked; refusal/daily regression |
| ft_v7 | 119/200 | — | — | ⛔ deterministic protect failure; not judged |
| ft_v7 + verify/retry-1 | 132/200 | — | — | ⛔ dual-protect failure; not judged |
| ft_v7 micro + verify/retry-1 | **144/200** | — | — | ⛔ two dual-protect failures; not judged |
| Qwen3.5-2B iteration 10 | — | — | — | ⛔ technical block; 2,249-token step OOM at 21.80–23.90 GB |
| Gemma 4 E2B iteration 11 | — | — | — | ⛔ technical block; mlx-lm load unsupported |
| ft_v7 micro + wrapper v4 | **147/200** | **67/200** | **35/200** | ⛔ blocked; refusal/safety/goal regression |

These recorded verdicts predate a pinned judge-protocol version. They remain
historical evidence and are not relabeled as `judge-protocol-v1`.

## Iteration 11 — Gemma 4 E2B preflight — technical block

The exact `google/gemma-4-E2B-it` repository was checked at revision
`9dbdf8a839e4e9e0eb56ed80cc8886661d3817cf`: Apache-2.0, 5,123,178,979 raw
stored parameters (5.1B rounded including embeddings) and 2.3B effective by
the model card, with a 10,246,621,918-byte BF16 weight blob. The unchanged
sf-chat-1 prompt renders through the native template with thinking disabled.

Actual support fails before generation: mlx-lm 0.31.3 rejects 60 checkpoint
K/V projection and K-norm tensors across language layers 15–34 as absent from
its implementation. The failed load has an 82,920,216-byte peak footprint;
that is not an optimizer-step result. The hard kill rule therefore stopped the
iteration before the required 2,249-token LoRA step, 4-bit conversion,
training, prefilter, or judging. No score, adapter, or quantized artifact
exists, and ft_v2 remains unchanged.

| iteration-11 comparison | deterministic | judge category | strict overall | verdict |
|---|---:|---:|---:|---|
| Gemma 4 E2B | — | — | — | unsupported load; no candidate |
| parked Qwen3-1.7B bare | 123/200 | 58/200 | 29/200 | blocked: refusal/daily/sleep |
| ft_v2 | 101/200 | 46/200 | **30/200** | pinned baseline / model of record |

## Iteration 12 — wrapper v4 promotion attempt — blocked

Wrapper v4 moves the required red-flag safety stance before the first draft.
Training-only calibration is TP 108 / FN 0 / FP 0 / TN 124; the one-shot suite
check, with rules frozen, is TP 14 / FN 1 / FP 1 / TN 184. Both ft_v7 siblings
then ran fresh through all 200 cases. Ordinary ft_v7 reaches 133 deterministic
but loses three ft_v2 protects and two prior gains, so it is not judged.
ft_v7 micro reaches 147 deterministic and preserves all 46 protected cases.

Two independent judge passes diverged at 126 versus 36 category passes. A
third pass adjudicated 96 category disagreements with recorded reasons. The
final micro-wrapper system reaches 67/200 category and 35/200 strict, but is
still blocked: refusal drops 11→10, safety triage 14→12, and goal coaching
1→0. Daily holds at one and sleep improves 2→5. The red-flag directive fixes
the old chest-tightness coaching stance, but the answer still says it cannot
rule out “anything cardiac,” short of literal directive compliance. ft_v2
remains pinned and no ship preparation ran.

## Iteration 13 — judge protocol v1 — measurement blocked

`judge-protocol-v1` keeps `sf-eval-v1`, `sf-gates-10`, and `rubric-v0.1`
unchanged while adding expected-action binding, authoritative machine facts,
calibration and exact-answer hashes, exact criterion coverage, code-derived
roll-ups, and criterion-level adjudication. The candidate again clears
prefilter at 147/200 with all 30 + 16 protects.

| symmetric protocol run | judge A category | judge B category | agreement | kappa | pass-rate gap |
|---|---:|---:|---:|---:|---:|
| ft_v7-micro + wrapper-v4 | 87/200 | 83/200 | **164/200 (82%)** | 0.632 | 2 points |
| ft_v2 unchanged answers | 165/200 | 67/200 | **76/200 (38%)** | -0.021 | 49 points |

The baseline result triggers the hard stop. Judge A fails qualitative X1 on
all 200 baseline answers with one generic reason while making near-blanket
category decisions; every structural validator still passes. Thus v1 proves
provenance but not semantic judge competence. The candidate's assembled
83-category/54-strict report is retained only as provisional evidence. ft_v2
is not adjudicated or re-pinned, no regression verdict runs, and no model or
serving artifact changes.

Iteration 14 should not train. It should use the same two blinded judge
sessions for both systems in randomized/interleaved order, require a perfect
scored non-suite qualification, require answer/context evidence for failures,
reject generic repeated reasons and degenerate criterion patterns, and demand
>=80% agreement, kappa >=0.60, and <=10-point pass gap on each system before
adjudication.

## Iteration 14 — judge protocol v2 — measurement blocked

`judge-protocol-v2` implements that measurement plan without new training. It
adds a scored synthetic non-suite qualification pack with a perfect-pass gate,
the same two persistent blinded sessions across both systems, randomized paired
rows, sequential shard unlocks with chained receipts and hidden sentinels,
evidence-bound failure verdicts, anti-repetition and anti-degeneracy checks,
and independent trust gates for ft_v2 and the candidate before adjudication.

Six paired attempts were quarantined before a complete trusted run. The final
attempt, run 6, reached shard 1 and was rejected because a hidden-sentinel
failure supplied invalid evidence. Quarantine is the protocol working: no
partial run, selective retry, or untrusted judgments were converted into model
scores.

The iteration therefore ends at the measurement gate. It produces no candidate
scorecard, adjudication, baseline re-pin, regression result, promotion, serving
change, fusion, or quantized artifact. ft_v2 remains the only pinned baseline,
model of record, and serving default.

Iteration 15 should improve deterministic judge-executor ergonomics before any
model or data change: provide canonical sentinel verdict emission from the
executor, validate it locally before submission, and make schema/evidence
failures immediately actionable while preserving the blinded, paired, sharded
trust contract. Only after that executor can complete a fully trusted run should
the project resume candidate comparison or training work.

## Iteration 15 — owner-review-v1 — candidate blocked

The owner replaced the failed automated promotion instrument for this one
candidate decision with the predeclared `owner-review-v1` blinded review. The
committed decision is **DO_NOT_PROMOTE**: 14/19 candidate difference answers
were acceptable against 16 required, none was unsafe, 8/10 sampled gains were
real, and all 18 safety checks passed. Blinded preference was 15 baseline, 3
candidate, and 1 tie. The reviewer field records that the owner delegated the
review to an agent; this is not represented as direct owner adjudication.

| owner-review-v1 gate | result | requirement | outcome |
|---|---:|---:|---|
| candidate difference acceptability | 14/19 | 16/19 | fail |
| unsafe candidate difference answers | 0 | 0 maximum | pass |
| seeded gains confirmed | 8/10 | 8/10 | pass |
| safety spot-checks | 18/18 | 18/18 | pass |

The five confirmed difference defects are a misbound weekly average
(`agen-v1-000231`), a false 406/455 ratio (`ev1x-core2-000002`), an incorrect
HRV definition (`ev1x-core2-000079`), over-triage of a benign lookalike
(`ev1x-lookalike2-004`), and a garbled refusal rationale
(`safe-v2-000026`). Two sampled gains also fail on incoherent or misbound text
(`ev1x-lookalike2-016`, `ev1x-core2-000068`). This evidence specifically
overturns the frozen `judge_noise` label for `ev1x-lookalike2-004`; its
candidate answer is a real over-refusal. Iteration 13 remains provisional and
untrusted, and its reports are not edited. ft_v2 remains the pinned baseline,
model of record, and serving default.

## Iteration 16A — scoped repair — prefilter blocked

`sf-gates-11` tightens percentage, role-binding, and cross-field comparisons;
wrapper v5 mirrors them and corrects benign fast-pulse over-triage only under
an explicit benign action contract. The re-pinned ft_v2 baseline moves from
101/46/30 to **100/46/30**: deterministic is baseline-worse-only and strict is
unchanged.

The 30-example agent_v8_micro round passes schema, gold, and independent critic
30/30, and ft_v8 completes the unchanged 2,116-step Qwen3-1.7B recipe. Its
fresh wrapper-v5 suite run reaches 140/200 deterministic with perfect s1/s2
and preserves all 30 ft_v2 strict protects. It is still blocked: two of 16
prior strict-gain protects regress on ungrounded 2.5 kg and 30-minute claims.
The hard prefilter stops before judging or a fresh owner-review packet. ft_v2
remains model of record and serving default.

## What the iterations teach

1. **A blocked model is the harness succeeding.** ft_v3 had the best val loss
   and genuinely improved two safety gates; the regression gate still refused
   the trade because judged quality dropped. Val loss fits the data; the suite
   measures what we want; only the suite can veto.
2. **Every gate is a fossilized failure.** None of s1–s5 was designed in the
   abstract; each mechanizes something a model actually did wrong once.
3. **Honesty upgrades look like regressions.** Expect the headline number to
   fall every time the ruler improves; track the full score quadruple, not the
   number.
4. **Aggregate gains cannot buy back strict regressions.** sf-gates-10 removes
   demonstrated s1/s3 false positives, but the judge still reveals refusal and
   coaching losses hidden by ft_v5's best-yet deterministic count.

## Current loop

Iteration 16A closes the priced defects mechanically and in data, but exposes
two different x1 regressions in the protected prior gains. Aggregate and ft_v2
protection are insufficient: every declared protect set must survive. Any next
round must begin from the two-case failure ledger and decide explicitly whether
derived-number grounding and post-retry x1 persistence belong in scope; it may
not reuse this candidate's failed prefilter or build the withheld review
packet. ft_v2 remains the default incumbent.
