# Iteration 14 verdict — measurement blocked under judge-protocol-v2

Quadruple attempted: `(sf-eval-v1, sf-gates-10, rubric-v0.1,
judge-protocol-v2)`.

Iteration 14 implemented the required measurement protocol, but no paired run
completed all 20 shards. The terminal state is **measurement blocked**, not a
candidate pass or failure. No trusted 200-case per-system agreement, kappa,
pass-gap, scorecard, adjudication, baseline re-pin, regression verdict, or
promotion artifact exists.

## Protocol and qualification evidence

The v2 controller gives the same two persistent blinded sessions both
systems, randomized and interleaved in 20 chained shards. Each shard contains
ten matched ft_v2/candidate cases plus two hidden qualification sentinels.
Later shards stay locked until both prior-session receipts and the paired
agreement artifact validate. A failure quarantines the whole attempt and
forbids selective retry.

Before suite access, each session must score a perfect 240/240 on the frozen
26-case non-suite pack (SHA-256
`8de7c5eeead43d02f6d5996319792bd2884ed401419549de0c57279c48b74e7a`).
The pack covers pass and fail for all 37 judge-owned criteria. Suite failures
must carry allowed reason codes, row-specific explanations, and verified exact
answer quotes and/or context pointers. Batch guards reject repeated generic
reasons/evidence and blanket criterion patterns. Downstream tools require a
trusted receipt proving >=80% agreement, kappa >=0.60, and <=10-point
pass-rate gap independently for both systems over all 200 cases.

## Retained paired-attempt ledger

| attempt | accepted evidence | terminal quarantine |
|---|---|---|
| 1 (`paired_run/`, seed 1402) | both qualification receipts | shard 0: session B repeated generic failure templates for X1, X2, and G1 |
| 2 (seed 1403) | both perfect qualifications; shards 0–1 valid | shard 2: session A marked S1 `contradicted` without the mandatory context pointer |
| 3 (seed 1404) | both perfect qualifications; shard 0 valid | shard 1: session A passed sentinel decisions but missed frozen D2/D3 gold evidence anchors |
| 4 (seed 1405) | both perfect qualifications | shard 0: paired semantic audit found session A failed X1 on all ten candidate rows |
| 5 (seed 1406) | both perfect qualifications; shard 0 valid | shard 1: session A reused one normalized X1 contradiction explanation three times |
| 6 (seed 1407) | both perfect qualifications; shard 0 valid; session A shard 1 valid | shard 1: session B passed the sentinel decision vector but its D3 answer quote missed frozen gold evidence |

Every failed attempt was retained; no failed row was edited and no session was
selectively retried. After five quarantines, run 6 was explicitly declared the
last operational attempt before its judges saw suite data, preventing an
unbounded sequence of fresh-session retries from becoming judge shopping.

## Final run evidence

Run 6's fresh sessions both qualified 240/240 with gold evidence validated:

| session | qualification receipt SHA-256 |
|---|---|
| A | `abdf637c770bae1faaa2f684d1b8554e80a9029286def6980f9db0022bfc78da` |
| B | `c83cb99133f0f0c20aa87f25922e7481149378264d25fc25632060f470f90973` |

The only paired run-6 agreement artifact is shard 0. These ten cases per
system are diagnostics, not the declared 200-case trust gate:

| system | category agreement | criterion agreement | kappa | pass A | pass B | pass gap |
|---|---:|---:|---:|---:|---:|---:|
| ft_v2 | 9/10 (90%) | 71/80 (88.75%) | 0.7368 | 30% | 20% | 10 points |
| candidate | 9/10 (90%) | 73/80 (91.25%) | 0.7368 | 30% | 20% | 10 points |

Session A's shard-1 receipt is valid, but session B failed the hidden
qualification sentinel (`jqv2-daily-compound-fail`, D3 answer quote). The
controller wrote `paired_run_6/QUARANTINE.json` and stopped before a shard-1
agreement artifact. It is invalid to extrapolate shard 0 into either system's
full-suite statistics.

## Consequences and iteration 15 recommendation

The historical ft_v2 101/46/30 report remains the only pinned baseline. The
candidate's v1 provisional result stays quarantined. V2 produced no model
scorecards, so `merge_judgments`, adjudication, `apply_judge`, baseline re-pin,
`check_regression`, serving changes, fusion, 4-bit conversion, and quantized
full-suite re-evaluation were not authorized.

Iteration 15 should remain measurement-only until execution is reliable. Keep
the suite, rubric, gates, protocol, qualification pack, evidence semantics,
and trust thresholds unchanged. Replace manual free-form JSON construction
with a structured judge executor that selects evidence from exact source
spans/pointers, runs the public validator locally before submission, preserves
the persistent paired identities, and emits the same receipt-bound artifacts.
Do not train, tune wrapper wording, re-pin a baseline, or retry fresh judges
until that executor can complete the frozen qualification/sentinel lifecycle
without weakening any gate.
