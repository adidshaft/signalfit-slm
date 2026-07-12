# SignalFit-SLM documentation

This index separates current operating documentation from historical research
records. Contributors should start with the current guides and consult history
only when a decision needs provenance.

## Start here

| Document | Purpose |
|---|---|
| [`product_brief.md`](product_brief.md) | Product scope and intended behavior |
| [`testing_guide.md`](testing_guide.md) | Run the shipped model and frozen suite |
| [`using_and_finetuning.md`](using_and_finetuning.md) | Use or fine-tune the system |
| [`pipeline_map.md`](pipeline_map.md) | Visual map of data, training, evaluation, and serving |
| [`components/`](components/README.md) | Component-by-component technical reference |

## Contracts and policy

| Document | Purpose |
|---|---|
| [`schema_design.md`](schema_design.md) | Context and training schema design |
| [`finetuning_format.md`](finetuning_format.md) | Chat and dataset format contracts |
| [`safety_policy.md`](safety_policy.md) | Safety precedence and response rules |
| [`eval_plan.md`](eval_plan.md) | Evaluation-suite design and invariants |
| [`eval_rubrics.md`](eval_rubrics.md) | Human and model-judge criteria |
| [`persona_library.md`](persona_library.md) | Synthetic persona coverage |

## Training and promotion

| Document | Purpose |
|---|---|
| [`data_generation_plan.md`](data_generation_plan.md) | Synthetic-data factory plan |
| [`distillation_plan.md`](distillation_plan.md) | Distillation and model-selection plan |
| [`promotion_procedure.md`](promotion_procedure.md) | Required candidate promotion process |
| [`PROMOTION_DECISION_ft_v10.md`](PROMOTION_DECISION_ft_v10.md) | Current model-of-record decision |
| [`coverage_backlog.md`](coverage_backlog.md) | Known coverage work |

## History

| Document | Purpose |
|---|---|
| [`process_guide.md`](process_guide.md) | Narrative build and evaluation process |
| [`project_history.md`](project_history.md) | Detailed dated iteration archive |

Scores are meaningful only with their suite, gate, rubric, and judge-protocol
versions. Do not copy an isolated score without those identifiers.
