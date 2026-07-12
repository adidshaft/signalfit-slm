# Security Policy

## Supported version

Security fixes are applied to the current `main` branch. Historical model and
evaluation artifacts are retained for reproducibility but are not maintained
as independent release lines.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting flow:

<https://github.com/adidshaft/signalfit-slm/security/advisories/new>

Include the affected path or commit, impact, reproduction steps, and any safe
mitigation you have identified. Please do not open a public issue for a secret,
privacy leak, unsafe deserialization path, dependency vulnerability, or a model
behavior that could cause material harm.

You should receive an acknowledgement within seven days. Fix timing depends on
severity and the ability to reproduce the report.

## Health-data privacy

Never include real wearable exports, medical information, authentication
tokens, or other personal data in a report. Use a minimal synthetic example.
If private data was committed or attached accidentally, say so in the private
report without reproducing the data again.

## Scope

Security reports can cover repository tooling, release artifacts, data leakage,
prompt or context injection that defeats deterministic protections, and unsafe
behavior that bypasses the documented safety policy. General model-quality
feedback belongs in the model-behavior issue form.
