# Pipeline Map — every component, one picture at a time

Four diagrams, ordered the way the system actually works:

1. **The data factory** — how a training example comes to exist
2. **The scoring machine** — how a model earns (or is denied) a score
3. **The gate evolution** — which failure gave birth to which gate
4. **The model iterations** — what each round changed, found, and fixed

Everything named here exists in the repo; file paths are real. Scores are only
meaningful as the triple **(eval suite, gate version, rubric version)**.

Prose reference for every component shown below:
[`components/`](components/README.md) (one file per subsystem). The narrative
of *why* each piece exists: [`process_guide.md`](process_guide.md).

---

## 1. The data factory

The core idea: **numbers are deterministic, only language comes from a model.**
Contexts are simulated (so "your 30-day average" is the true mean of a real
series), every citable number is enumerated in `allowed_numbers`, and machine
gates check everything before a human-quality critic ever sees it.

```mermaid
flowchart TD
    subgraph CONTRACTS["Design contracts (written BEFORE any training)"]
        ATRIA["Atria reference app<br/>(read-only; source of the<br/>fabrication-check idea)"]
        SCHEMA["sf-context-1 schema<br/>schemas/assistant_context.schema.json<br/>provider-agnostic, nullable,<br/>missing_fields, per-field confidence"]
        TRAINSCHEMA["sf-train-1 schema<br/>schemas/training_example.schema.json"]
        POLICY["docs/safety_policy.md<br/>refuse / triage / hedge rules"]
        RUBRICS["docs/eval_rubrics.md<br/>rubric-v0.1: X1–X7 cross-cutting<br/>+ per-category criteria"]
        PERSONA["docs/persona_library.md"]
        ALLOWED["allowed_numbers contract:<br/>every number the model may say<br/>is enumerated in the context"]
        ATRIA -->|inspired| ALLOWED
        SCHEMA --> ALLOWED
    end

    subgraph SAMPLER["Context sampler (deterministic)"]
        SIM["simulated 30-day physiology series<br/>(coherence by construction)"]
        SPECS["scripts/make_context_specs.py<br/>deterministic context specs,<br/>chunked 10 × 30"]
        SIM --> SPECS
    end

    subgraph FACTORY["Agent data factory (no paid API)"]
        GEN["GENERATOR subagents<br/>write question + answer + labels<br/>per spec; run validator themselves"]
        VAL["scripts/validate_schema.py — HARD GATE<br/>JSON-Schema validity + grounding<br/>+ missing-fields consistency<br/>(exit non-zero = rejected)"]
        CRITIC["CRITIC subagents<br/>qualitative review vs rubrics:<br/>brands, follow-up budget,<br/>anti-conservatism, safety precedence"]
        CURATED["data/synthetic/curated/*<br/>committed per chunk"]
        GEN --> VAL --> CRITIC --> CURATED
    end

    subgraph ROUNDS["Data rounds (each aimed at a measured failure)"]
        SEED["seed_v0: 30 template examples<br/>+ 2 hand-written worked_examples"]
        V1DATA["agent_v1: 300 general<br/>(10 task categories)"]
        V2DATA["agent_v2_safety: 100<br/>40 triage / 30 refusal /<br/>30 benign lookalikes"]
        V3DATA["agent_v3_relational: 150<br/>110 answer / 30 refuse / 10 triage<br/>(6 chunks; 0 lookalikes — known gap)"]
    end

    subgraph PREP["Dataset build (deterministic, manifest-hashed)"]
        PREPARE["scripts/prepare_dataset.py<br/>example JSON → sf-chat-1 JSONL<br/>system prompt sft-sys-1 (pinned)<br/>+ sha256 manifest"]
        SPLIT["scripts/split_dataset.py<br/>train / valid / eval —<br/>persona-disjoint, locked eval isolated"]
        FTDATA["data/ft_v1 · ft_v2 · ft_v3<br/>(ft_v3: train 461 / valid 51 / eval 40)"]
        PREPARE --> SPLIT --> FTDATA
    end

    subgraph TRAIN["Training (MLX LoRA on a Mac)"]
        BASE["Qwen2.5-1.5B-Instruct<br/>Apache-2.0 (license-checked;<br/>3B is research-only → benchmark only)"]
        LORA["mlx_lm lora<br/>training/configs/*.yaml<br/>adapters, not full weights"]
        ADAPTERS["models/adapters/<br/>ft_v1 (val 1.87→0.38)<br/>ft_v2 (→0.42) · ft_v3 (→0.284)"]
        BASE --> LORA --> ADAPTERS
    end

    subgraph SERVE["Serving / shipping"]
        ASK["scripts/ask.py<br/>one-command Q&A vs a context JSON<br/>+ on-the-fly grounding warning"]
        FUSE["mlx_lm fuse → convert -q<br/>4-bit (~0.9 GB)"]
        IOS["iOS via MLX Swift (MLXLLM)"]
        FUSE --> IOS
    end

    CONTRACTS --> SAMPLER
    SPECS --> GEN
    POLICY --> GEN
    RUBRICS --> CRITIC
    TRAINSCHEMA --> VAL
    SEED --> PREPARE
    CURATED --> V1DATA & V2DATA & V3DATA
    V1DATA & V2DATA & V3DATA --> PREPARE
    ADAPTERS --> ASK
    ADAPTERS --> FUSE

    REAL["data/real_world/<br/>real tracker exports — LOCAL ONLY,<br/>never committed, never trained on;<br/>contributes failure SHAPES, not values"]
    REAL -.->|failure shapes only| ROUNDS
```

Also in the repo but deliberately parked: `scripts/generate_teacher_batch.py`
(the paid Batch-API teacher path — built, dry-run verified, descoped in favor
of the agent factory) and `scripts/generate_seed_dataset.py` (the template
engine behind seed_v0).

---

## 2. The scoring machine

A model never grades itself against a moving target. The suite is **frozen**
(hash-manifested, append-only, contamination-checked), the gates are
**versioned**, the judge runs **twice independently**, and the final word
belongs to a **regression gate** against a pinned baseline.

```mermaid
flowchart TD
    subgraph SUITE["Frozen eval suite — eval/v1 (sf-eval-v1, 66 cases)"]
        CORE["core/ — 40 locked eval cases<br/>(same distribution as training)"]
        ADV["adversarial/ — 14 cases<br/>PED fiction/third-party/medicalized,<br/>ED compensation/punishment framings,<br/>symptom minimization, metric-reassurance bait,<br/>+ 3 benign lookalikes (must NOT refuse)"]
        BIND["binding/ — 12 field-binding probes<br/>decimal values, respiratory-vs-RHR distractors,<br/>today-vs-trend traps, derived deltas"]
        FREEZE["scripts/freeze_eval.py build / check<br/>sha256 per case, append-only,<br/>train/valid contamination guard"]
        GOLD["gold_generations.jsonl<br/>gold answers of all 66 cases<br/>→ gate calibration: must pass 100%"]
        CORE & ADV & BIND --> FREEZE
        FREEZE --> GOLD
    end

    subgraph GENSTEP["Answer generation"]
        GENANS["scripts/generate_answers.py<br/>--examples mode (suite slices)<br/>or split mode (eval.jsonl)"]
    end

    subgraph GATES["Deterministic gates — scripts/run_eval.py (GATE_VERSION = sf-gates-5)"]
        X["x1 grounding · x4 ≤1 question<br/>x5 no brands · x6 length"]
        S12["s1 no-coaching-in-triage<br/>s2 no-protocol-in-refusal"]
        S3["s3 field binding<br/>(metric phrase → exact field, avg-aware)"]
        S4["s4 comparative arithmetic<br/>(direction/closeness claims verified)"]
        S5["s5 claim discipline<br/>(false missing-data claims,<br/>diagnosis language in triage)"]
        REPORT["eval_report.json<br/>stamped with gate + rubric version,<br/>per-gate + per-category rates"]
        X & S12 & S3 & S4 & S5 --> REPORT
    end

    subgraph JUDGE["LLM judge (agent workflow, rubric-v0.1)"]
        BUNDLE["judge_bundle.jsonl<br/>one self-contained prompt per answer:<br/>rubric section + context + labels + answer"]
        PA["judge pass A<br/>(independent agent)"]
        PB["judge pass B<br/>(independent agent)"]
        MERGE["scripts/merge_judgments.py<br/>agreement → strict-AND verdict"]
        DISPUTE["disagreements.jsonl<br/>→ human/main-agent adjudication,<br/>reasoning recorded"]
        APPLY["scripts/apply_judge.py<br/>overall_pass = gates AND category<br/>AND every judge criterion"]
        JUDGED["judged_report.json"]
        BUNDLE --> PA & PB --> MERGE
        MERGE --> DISPUTE --> APPLY
        MERGE --> APPLY --> JUDGED
    end

    subgraph REGGATE["Regression gate"]
        BASELINE["eval/v1/baseline/ft_v2.judged_report.json<br/>(pinned; re-pinned ONLY when the<br/>gate version bumps, same commit)"]
        CHECK{"scripts/check_regression.py"}
        SHIP["✅ ship candidate:<br/>matches or beats baseline<br/>on every gated metric"]
        BLOCK["⛔ BLOCK (exit 1):<br/>gate/rubric/suite mismatch,<br/>ANY safety-gate drop (zero tolerance),<br/>any category or overall drop"]
        BASELINE --> CHECK
        CHECK -->|no regression| SHIP
        CHECK -->|any drop| BLOCK
    end

    ADAPTER["model adapter under test"] --> GENANS
    FREEZE -->|66 cases| GENANS
    GENANS --> GATES
    REPORT --> BUNDLE
    GOLD -.->|calibration input| GATES
    JUDGED --> CHECK
```

**Calibration rule** (applies to every new gate before it may score anything):
all 66 gold answers pass — zero false positives — AND the known failures are
still caught — zero lost recall. One draft s3 flag failed this rule and turned
out to be a gate bug, not a model bug; that is why the rule exists.

---

## 3. The gate evolution — every gate was born from a caught failure

```mermaid
flowchart LR
    G1["sf-gates-1<br/>x1 grounding, x4 followups,<br/>x5 brands, x6 length"]
    G2["sf-gates-2<br/>+ s1 no-coaching-in-triage<br/>+ s2 no-protocol-in-refusal<br/>(spelled-number + negation aware)"]
    G3["sf-gates-3<br/>+ s3 field binding<br/>(today + trend bindings, avg-aware)"]
    G4["sf-gates-4<br/>+ s4 comparative arithmetic<br/>(direction + closeness vs bound field)"]
    G5["sf-gates-5<br/>+ s5 claim discipline<br/>(false missing-data / baseline claims,<br/>diagnosis language in triage)"]
    G6["sf-gates-6<br/>x5 brand matcher uses word boundaries<br/>(no score change; removes substring false positives)"]

    F1(["ft_v1 eval: a triage answer coached,<br/>a refusal leaked protocol shape<br/>('four weeks on' — spelled out,<br/>invisible to the digit regex)"])
    F2(["real-data test (local Atria/WHOOP export):<br/>respiratory rate quoted as resting HR,<br/>trend strain quoted as today's strain,<br/>invented deltas"])
    F3(["first judge run: X1 false relations 34/66 —<br/>grounded values, arithmetically false claims<br/>('6.9h comfortably above your 7.5h average')"])
    F4(["ft_v3 round: unsupported qualitative labels<br/>('green light', 'not reflux'),<br/>false 'I can't see your sleep log' claims"])
    F5(["gold calibration caught 'oura' inside 'encourage' —<br/>a gate bug, not a model failure"])

    G1 --> F1 --> G2 --> F2 --> G3 --> F3 --> G4 --> F4 --> G5 --> F5 --> G6

    style F1 fill:#8b1e1e,color:#fff
    style F2 fill:#8b1e1e,color:#fff
    style F3 fill:#8b1e1e,color:#fff
    style F4 fill:#8b1e1e,color:#fff
    style F5 fill:#8b1e1e,color:#fff
```

Two rules keep this honest: a gate change **bumps `GATE_VERSION`** (reports
carry the stamp; `check_regression.py` refuses cross-version comparison), and
each honesty upgrade is allowed to make the headline number *worse* — 37/40 →
34/40 → 9/40 core-strict — because none of those drops changed the model, only
how much of it we could see.

---

## 4. The model iterations — the improvement loop, four times around

```
eval failure → make it DETERMINISTIC (new gate) → generate TARGETED data
     ▲                                                      │
     └────────── re-evaluate ◄──── re-train (LoRA) ◄────────┘
```

```mermaid
flowchart TD
    subgraph IT1["Iteration 1 — ft_v1 (phase 1)"]
        D1["train: 245 of agent_v1 300<br/>+ seed heritage"]
        T1["LoRA 600 iters, val 1.87 → 0.38"]
        E1["locked-30 eval: grounding 100%,<br/>shape learned — but safety under-learned:<br/>1/2 triage coached, refusal drifted"]
        D1 --> T1 --> E1
    end

    subgraph IT2["Iteration 2 — ft_v2 (phase 2a)"]
        FIX1["response: s1+s2 gates (sf-gates-2)<br/>+ agent_v2_safety 100 examples<br/>(30% benign lookalikes vs over-refusal)"]
        T2["LoRA 750 iters, val → 0.42"]
        E2["triage 6/6, zero protocol leakage,<br/>lookalikes still coached —<br/>targeted data beat more data"]
        FIX1 --> T2 --> E2
    end

    subgraph HARNESS["Phase 2b part 1 — build the real ruler (no retrain)"]
        RD["real-data test → s3 gate (sf-gates-3)"]
        FZ["suite frozen: sf-eval-v1, 66 cases<br/>core 40 + adversarial 14 + binding 12"]
        JG["judge actually run, double-pass:<br/>ft_v2 honest = 57/66 gates,<br/>18/66 judge, 11/66 strict overall"]
        FIND["findings: X1 false relations 34/66;<br/>fiction-framing PED jailbreak WORKS<br/>(s2 caught it); binding 1/12"]
        PIN["baseline pinned:<br/>eval/v1/baseline/ft_v2.judged_report.json"]
        RD --> FZ --> JG --> FIND --> PIN
    end

    subgraph IT3["Iteration 3 — ft_v3 (phase 2b part 2)"]
        G4B["s4 comparative-arithmetic gate<br/>(sf-gates-4; flags 17/34 X1 fails,<br/>0 false positives)"]
        D3["agent_v3_relational: 150 examples<br/>(relational correctness + indirect safety;<br/>lookalikes missing — known gap)"]
        T3["ft_v3: LoRA 1060 iters, val → 0.284"]
        E3["full workflow: gates + double judge<br/>+ 3 adjudications"]
        REG{"check_regression.py<br/>vs pinned ft_v2 baseline"}
        BLOCKED["⛔ BLOCKED — net regression:<br/>strict 11→10, sleep/goal/triage dropped.<br/>s3 66/66 (+4), s2 11/11 (+2) improved,<br/>but s4 49→46: the target got WORSE.<br/>Baseline stays ft_v2."]
        G5B["post-mortem → s5 claim-discipline<br/>gate (sf-gates-5); next round:<br/>claim discipline + missing lookalikes"]
        G4B --> D3 --> T3 --> E3 --> REG --> BLOCKED --> G5B
    end

    subgraph IT4["Iteration 4 — ft_v4 (phase 2b part 3)"]
        G6B["sf-gates-6 calibration fix<br/>+ agent_v4_discipline 150 examples<br/>(claim discipline, relations, lookalikes, safety)"]
        T4["ft_v4: LoRA 1371 iters,<br/>best val 0.281, final 0.354"]
        E4["full workflow: deterministic 44/66,<br/>judge category 19/66, strict 13/66;<br/>59 judge agreements + 7 adjudications"]
        REG4{"check_regression.py<br/>vs pinned ft_v2 baseline"}
        BLOCKED4["⛔ BLOCKED — aggregate gains,<br/>but s1 triage safety fell 10/10→9/10;<br/>sleep strict 1/6→0/6 and goal strict 1/5→0/5.<br/>Baseline stays ft_v2."]
        NEXT["next loop: s4/X1 grounding<br/>+ replay agen-v1-000232;<br/>preserve s2 and s3 gains"]
        G6B --> T4 --> E4 --> REG4 --> BLOCKED4 --> NEXT
    end

    E1 --> FIX1
    E2 --> RD
    PIN --> G4B
    G5B --> G6B

    style BLOCKED fill:#8b1e1e,color:#fff
    style BLOCKED4 fill:#8b1e1e,color:#fff
    style JG fill:#1e5c8b,color:#fff
```

**Scoreboard** (all under the triple sf-eval-v1 / sf-gates-6 / rubric-v0.1):

| model | deterministic | judge category | strict overall | verdict |
|---|---:|---:|---:|---|
| ft_v2 | 41/66 | 18/66 | **11/66** | pinned baseline, model of record |
| ft_v3 | 39/66 | 11/66 | 10/66 | ⛔ blocked by regression gate |
| ft_v4 | **44/66** | **19/66** | **13/66** | ⛔ blocked by s1 safety regression |

Both blocked retrains are the harness working as designed. ft_v4 improved all
three aggregate counts plus refusal safety and field binding, but the regression
gate saw one new triage-coaching failure and refused the trade. That refusal —
automatic, versioned, non-negotiable — is what the phase-2b ruler was built for.
