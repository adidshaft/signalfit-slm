# Root cause: the sleep-arithmetic failures are a train/test coverage gap

## Finding

The recurring `ev1x-core2-000002` failure — present across iterations 16A, 17A,
and 18A and repeatedly misattributed to "capability variance at 1.7B" — has a
concrete, fixable cause: **the training data never contains the sleep fields
the eval suite tests.**

The seed simulator (`generate_seed_dataset.py::build_context`) emits only
`today.sleep.duration_minutes`. The eval suite's core2 contexts additionally
carry, in **zero** training examples:

- `today.sleep.debt_minutes`
- `today.sleep.need_minutes`
- `today.sleep.efficiency_pct`
- `derived.sleep_vs_need_minutes`
- `derived.sleep_vs_7d_avg_minutes`
- `baselines.baseline_30d.sleep_duration_minutes.{mean,sd,n}`
- `baselines.baseline_7d.sleep_duration_minutes.{mean,sd,n}`

The model is asked to reason about sleep debt vs need vs efficiency on a
vocabulary it was never trained on, then produces confused output ("keep the
debt to 455 minutes"; "55 ms running a bit short" when 55 > 52). **No amount of
seed variation fixes this** — the training distribution is missing the fields.

## Why this matters strategically

It reframes the iteration 18A "serving ceiling / capability wall" conclusion.
Part of that wall — the sleep arithmetic — is not a model-size limit at all; it
is a data-coverage hole. The correct fix is data, on the same locked
Qwen3-1.7B: add training examples that carry the debt/need/efficiency/derived
sleep fields with correct arithmetic golds. This is `agent_v10_micro`.

The PED-refusal failures (`agen-v1-000135`, `advs-v1-000002`) are a different,
softer problem — the model has crisp refusal exemplars in training but has not
fully generalized them; more targeted reinforcement should help, and it costs
nothing to add alongside the sleep coverage.

## Action

`agent_v10_micro`: sleep-debt coverage (fresh contexts carrying the missing
fields, correct directional arithmetic) + crisp PED-refusal reinforcement
(refuse plainly, name no protocol, redirect to a doctor for health not the
drug). Same student, no local teacher, no infrastructure.
