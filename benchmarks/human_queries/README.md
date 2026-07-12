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

## Screenshots

The four PNGs in `screenshots/` were produced with the built-in ChatGPT image
generation tool as full-bleed portrait app screenshots. They deliberately have
no device hardware frame. Each screenshot contains the corresponding real
prompt and model response from `responses.jsonl`.

### Recovery explanation

![SignalFit recovery explanation](screenshots/01-recovery.png)

### Training decision

![SignalFit training decision](screenshots/02-training.png)

### Sleep insight

![SignalFit sleep insight](screenshots/03-sleep.png)

### Safety triage

![SignalFit safety triage](screenshots/04-safety.png)
