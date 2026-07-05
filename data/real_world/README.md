# Real-world data (local only — never committed)

Everything in this directory except this README and the `.gitignore` is ignored by
git **by design**: real exports are personal health data and must not enter the
repo, the training set, or the locked eval set.

Purpose: local adapter development and spot-checking only — e.g. an Atria research
bundle (`atria-research-*.json.gz`) or raw export (`hr.csv`, `rr.csv`,
`sleeps.json`, `workouts.json`, `rollups.json` per Atria's `docs/export-schema.md`)
used to verify that the Atria→SignalFit adapter fills `sf-context-1` correctly.

Rules:
- Never copy values from real exports into synthetic examples or docs.
- Never relax the `.gitignore` here.
- Delete exports when done; nothing in this directory is a dependency of the build.
