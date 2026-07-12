# Provenance metadata repair (2026-07-13)

Commit `db8ea24` replaced internal agent display names in the committed ft_v2
judged report and 66 original evaluation cases as part of a public-attribution
cleanup. Scores, verdicts, criteria, case semantics, and model outputs did not
change, but the affected provenance hashes were not updated.

The pre-cleanup suite manifest is retained at
`eval/v1/manifest.pre-public-attribution-cleanup.json`. The active suite
manifest was rebuilt from all 200 sanitized cases, and this directory's
manifest and completed decision now record the sanitized report and suite
hashes with recomputed self-authenticating payload hashes. This restores the
provenance and freeze checks without changing review items, the decision rule,
the sealed mapping, model scores, or the promotion result.
