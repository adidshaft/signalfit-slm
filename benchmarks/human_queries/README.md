# SignalFit benchmark and screenshot set

Model: `data/checks/ship-ft_v10/export-4bit`  
Serving system: `answer-check-v7`  
Generated: 2026-07-13

## Canonical domain benchmark

The repository does not include a general-purpose MMLU, GSM8K, HumanEval, or
`lm-eval` harness. The valid existing benchmark is the frozen 200-case
SignalFit suite (`sf-eval-v1`, `sf-gates-13`). Its shipped report records:

| Check | Result |
|---|---:|
| Deterministic pass | 135/200 (68.0%) |
| Grounding | 182/200 (91.0%) |
| Follow-up discipline | 200/200 |
| Brand discipline | 200/200 |
| Length | 196/200 |
| Field binding | 196/200 |
| Comparative arithmetic | 143/200 |
| Claim discipline | 200/200 |
| No coaching during triage | 18/18 |
| No protocol in refusal | 19/19 |

Source: `data/checks/ship-ft_v10/eval_report/eval_report.json`.

## Fresh human-style benchmark

Four conversational prompts were run through the shipped 4-bit model and its
production wrapper. The set covers recovery explanation, a daily training
decision, sleep coaching, and medical-red-flag triage.

Result: **4/4 deterministic pass, 4/4 grounded, 4/4 field-bound, 4/4
comparative-arithmetic pass, and 1/1 triage safety pass.** No retry was needed;
the safety directive fired on the red-flag case as intended.

- Inputs: `cases/`
- Raw model outputs: `responses.jsonl`
- Wrapper trace: `correction_log.jsonl`
- Gate report: `eval_report/eval_report.json`
- Reproducible input builder: `../../scripts/prepare_human_benchmark.py`

## Conversation Screenshots

The documentation screenshots supplied for this benchmark are stored under
`screenshots/` and embedded below.

| Training guidance | Sleep insight | Sleep detail |
|---|---|---|
| <img src="screenshots/training-coach.png" alt="SignalFit training coach conversation" width="280"> | <img src="screenshots/sleep-coach-wide.png" alt="SignalFit sleep coach conversation" width="280"> | <img src="screenshots/sleep-coach-compact.png" alt="SignalFit detailed sleep coach conversation" width="280"> |
