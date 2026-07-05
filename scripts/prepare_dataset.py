#!/usr/bin/env python3
"""Convert SignalFit training examples to chat fine-tuning JSONL (format sf-chat-1).

Usage:
    .venv/bin/python scripts/prepare_dataset.py <file-or-dir> [...] -o data/ft_v0/all.jsonl

Implements docs/finetuning_format.md:
  - fixed system prompt sft-sys-1 (verbatim, versioned),
  - user message = "CONTEXT:\n<compact sorted context JSON>\n\nQUESTION: <q>",
  - context minus request.user_question and the whole task block,
  - assistant message = target_response.text,
  - sidecar <out>.manifest.json: per-line example_id/labels/sha256 + file sha256
    + format/version pins.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

FORMAT_ID = "sf-chat-1"
SYSTEM_PROMPT_ID = "sft-sys-1"
SYSTEM_PROMPT = (
    "You are SignalFit, a fitness assistant. Answer ONLY from the CONTEXT JSON. "
    "If a value is not in CONTEXT, say you don't have it — never estimate, never "
    "present population numbers as the user's own. Hedge on estimate-grade or "
    "low-confidence values. You are not a doctor and never diagnose; on medical "
    "red flags, stop coaching and recommend appropriate care."
)


def model_input_context(context: dict) -> dict:
    ctx = copy.deepcopy(context)
    ctx.get("request", {}).pop("user_question", None)
    ctx.pop("task", None)
    return ctx


def to_chat_line(example: dict) -> str:
    ctx_json = json.dumps(model_input_context(example["context"]),
                          separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    question = example["context"]["request"]["user_question"]
    record = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"CONTEXT:\n{ctx_json}\n\nQUESTION: {question}"},
            {"role": "assistant", "content": example["target_response"]["text"]},
        ]
    }
    return json.dumps(record, separators=(",", ":"), sort_keys=True, ensure_ascii=False)


def iter_example_files(args: list[str]):
    for arg in args:
        p = Path(arg)
        if p.is_dir():
            yield from sorted(p.rglob("*.json"))
        elif p.suffix == ".json":
            yield p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines, entries = [], []
    for path in iter_example_files(args.inputs):
        example = json.loads(path.read_text())
        line = to_chat_line(example)
        lines.append(line)
        entries.append({
            "line": len(lines),
            "example_id": example["example_id"],
            "task_category": example["task_category"],
            "case_type": example["case_type"],
            "provider_mask": example["labels"]["provider_mask"],
            "persona_id": example["labels"].get("persona_id"),
            "is_locked_eval": example["labels"].get("is_locked_eval", False),
            "sha256": hashlib.sha256(line.encode()).hexdigest(),
            "source_file": str(path),
        })

    body = "\n".join(lines) + "\n"
    out.write_text(body)
    manifest = {
        "format": FORMAT_ID,
        "system_prompt_id": SYSTEM_PROMPT_ID,
        "schema_version": "sf-context-1",
        "count": len(lines),
        "file_sha256": hashlib.sha256(body.encode()).hexdigest(),
        "examples": entries,
    }
    manifest_path = out.with_suffix(out.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {len(lines)} lines -> {out}\nmanifest -> {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
