# Iteration 13 verdict — measurement protocol blocked

Quadruple attempted: `(sf-eval-v1, sf-gates-10, rubric-v0.1,
judge-protocol-v1)`.

The protocol improved agreement on the iteration-12 candidate from 104/200
(52%) to 164/200 (82%; kappa 0.632, pass-rate gap 2 points). That result alone
was not enough: the required symmetric ft_v2 pass produced only 76/200 (38%;
kappa -0.021, pass-rate gap 49 points). The hard trust rule therefore stops
the iteration before a baseline re-pin or regression verdict.

## Evidence chain

| system | judge A category | judge B category | agreement | criterion agreement | status |
|---|---:|---:|---:|---:|---|
| ft_v7-micro + wrapper-v4 | 87/200 | 83/200 | 164/200 (82%) | 1,479/1,654 (89.4%) | candidate-side trust gate passed |
| ft_v2 unchanged answers | 165/200 | 67/200 | 76/200 (38%) | 1,237/1,654 (74.8%) | **protocol failed; hard stop** |

The candidate's assembled 83/200 category and 54/200 strict report is retained
as `provisional_untrusted_report.json`. It is not a verdict and must not be
compared with the historical baseline. ft_v2 was not adjudicated, no new
baseline file was created, and the existing baseline remains untouched.

## Failure diagnosis

The baseline confusion matrix is both-pass 54, both-fail 22, A-pass/B-fail
111, and A-fail/B-pass 13. Judge A failed qualitative X1 on all 200 answers
with the same generic reason while passing whole category families almost
uniformly (daily 22/22, explain 20/20, followup 14/14, plan 14/14). Judge B
passed X1 on 127/200 and applied those category criteria much more strictly.
Judge A also failed every habit criterion on all 12 habit cases. The schema,
hashes, and category AND checks all passed, proving that structural validation
cannot detect a semantically degenerate judge.

The experiment also used fresh isolated judge instances for ft_v2 rather than
the exact candidate A/B sessions. The prompt and calibration were identical,
but the 49-point swing shows that protocol text alone did not bind execution
strongly enough across judge instances. A candidate-only agreement gain was
therefore false reassurance.

The complete per-example failure ledger is `ft_v2/judge_disagreements.jsonl`
(198 rows, each retaining the original bundle and both reasons). No paid API,
training, generation, fusion, quantization, or serving change was made.

Housekeeping deleted only regenerated Python bytecode: 31 files across two
passes, 436,878 apparent / 499,712 allocated bytes. All model caches needed by
a possible promotion, final adapters, pinned bases, baselines, and evaluation
evidence were retained.

## Iteration 14 recommendation

Stay on the measurement layer; do not train. Build `judge-protocol-v2` around
paired, blinded judging of both systems by the same two judge sessions, with
randomized/interleaved system order. Replace read-only calibration with a
scored non-suite qualification that must be perfect before suite access.
Require evidence quotes or context JSON pointers for every failure, reject
generic repeated reasons and degenerate all-pass/all-fail criterion patterns,
and test these semantic guards on deliberately bad judge outputs. Require at
least 80% category agreement, kappa at least 0.60, and no more than a 10-point
pass-rate gap independently for ft_v2 and the candidate before adjudication.
Only then re-run the symmetric re-pin and regression chain.
