# Data layout

SignalFit keeps data lineage explicit because training and evaluation results
depend on exact inputs.

- `synthetic/`: curated synthetic source examples by generation round
- `ft_*`: prepared train, validation, and isolated eval splits plus manifests
- `checks/`: candidate and release evaluation artifacts
- `real_world/`: local-only wearable exports; ignored except for its policy files

## Contribution rules

- Never commit real health or wearable data.
- Do not lightly perturb a real person's values and call the result synthetic.
- Keep `eval/v1` isolated from train and validation splits.
- Preserve manifests and lineage metadata.
- Validate new examples before preparing a dataset.

```bash
.venv/bin/python scripts/validate_schema.py path/to/examples
```

See [`../CONTRIBUTING.md`](../CONTRIBUTING.md) and
[`../docs/data_generation_plan.md`](../docs/data_generation_plan.md).
