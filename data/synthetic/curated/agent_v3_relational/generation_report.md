# agent_v3_relational generation report

- count: 150
- chunks: 6
- mix: 90 relational correctness, 40 indirect safety, 20 benign lookalikes
- prompt_version: agent-v3-relational-1
- created_at: 2026-07-09

Validation:

- `scripts/validate_schema.py data/synthetic/curated/agent_v3_relational`: 150 passed, 0 failed.
- Target answers scored through `(agent-v3-relational, sf-gates-4, rubric-v0.1)`: deterministic 150/150; s4 comparative arithmetic 150/150; s1 triage 10/10; s2 refusal 30/30.
- `scripts/freeze_eval.py check --version v1`: suite sf-eval-v1 OK after generation.

Critic pass:

- Chunks 01-02: revised sleep lead correctness, recovery contributor ranking, and short strain-answer length.
- Chunks 03-04: revised recovery explanations to rank contributors with correlational language, strengthened triage care level, and added dangerous-cut acute risk language.
- Chunks 05-06: revised triage prompt/flag alignment, one-action benign lookalike coaching, and chest-soreness routing.
- Final focused rechecks accepted the revised examples.
