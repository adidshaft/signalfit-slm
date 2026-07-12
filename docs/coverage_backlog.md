# Field-coverage backlog (quality, NON-blocking)

A systematic train/eval field audit (all curated training contexts vs the 200
eval contexts) found **23 fields the eval tests that appear in zero training
examples** — the same class of gap that caused the sleep-arithmetic failure
(`docs/../data/checks/iteration18a-ft-v9-wrapper-v7/ROOT_CAUSE_sleep_fields.md`).

## Does it block the goal? No.

Of the 23, the higher-risk ones (`derived.*` comparison fields,
`baselines.baseline_7d.sleep_*`) appear in 5 eval cases. Two currently fail
(`bind-v1-000010`, `bind-v1-000011`) — but **both fail in the ft_v2 baseline
too, so neither is a protect case.** They do not block promotion of any
candidate. Recorded here rather than fixed now, to avoid turning a
non-blocking quality gap into another iteration.

## The uncovered fields, by risk

**Derived comparison fields (highest risk — same class as the sleep gap):**
`derived.hrv_vs_7d_avg_ms`, `derived.rhr_vs_7d_avg_bpm`,
`derived.load_vs_recent_avg`, `derived.avg_recent_training_load`,
`derived.avg_recent_ride_duration_minutes`,
`derived.today_vs_typical_ride_minutes`. The model is asked to cite
pre-computed deltas it never trained on.

**7-day sleep baseline stats:** `baselines.baseline_7d.sleep_duration_minutes.
{mean,sd,n}`.

**Deeper workout history:** `recent_workouts[2..4].{duration_minutes,avg_hr_bpm,
peak_hr_bpm,training_load}` — training data only carries `recent_workouts[0..1]`.

**Misc:** `user_stated.weekly_loss_rate_kg`, `request.intake`.

## If/when quality work is prioritized (post-promotion)

A follow-up micro-round on the agent_v10 pattern would add training contexts
carrying the `derived.*` fields and `recent_workouts[2..4]`, with correct
golds. This would likely lift `bind-v1-000010/011` and harden the model
against the whole class. It is a **quality** improvement, explicitly deferred
until after a model is promoted and shipped — it is not on the critical path
to the goal.
