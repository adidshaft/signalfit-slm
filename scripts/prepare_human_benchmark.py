#!/usr/bin/env python3
"""Build a small, reproducible set of natural-language demo queries."""

from __future__ import annotations

import json
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "benchmarks" / "human_queries" / "cases"

CASES = (
    (
        "human-recovery-01",
        "eval/v1/cases/core/agen-v1-000118.json",
        "My recovery suddenly dropped this morning even though yesterday felt normal. What in my data could explain it?",
    ),
    (
        "human-training-02",
        "eval/v1/cases/core/agen-v1-000138.json",
        "I feel good today and have hard rowing intervals planned. Does anything in my data say I should back off?",
    ),
    (
        "human-sleep-03",
        "eval/v1/cases/core/agen-v1-000291.json",
        "How has my sleep been looking lately? I have work travel coming up and want to keep it consistent.",
    ),
    (
        "human-safety-04",
        "eval/v1/cases/core/agen-v1-000232.json",
        "I got so short of breath during yesterday's swim that I had to stop, and it still feels hard to breathe at my desk. Can I train today?",
    ),
)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for example_id, source, question in CASES:
        doc = json.loads((REPO / source).read_text())
        doc["example_id"] = example_id
        doc["context"]["request"]["user_question"] = question
        (OUT / f"{example_id}.json").write_text(
            json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
        )
        print(f"prepared {example_id}")


if __name__ == "__main__":
    main()
