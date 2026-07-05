#!/usr/bin/env python3
"""Generate model answers for a prepared split (post-training step).

Usage:
    .venv/bin/python scripts/generate_answers.py data/ft_v0/eval.jsonl \
        --model Qwen/Qwen2.5-1.5B-Instruct \
        --adapter models/adapters/ft_v0_qwen2.5-1.5b \
        -o data/ft_v0/eval_generations.jsonl

Reads the chat JSONL (sf-chat-1) plus the sidecar manifest of the source
all.jsonl to recover example_ids, prompts the model with system+user messages,
and writes {"example_id", "answer"} lines for scripts/run_eval.py.

Requires mlx-lm (.venv/bin/pip install mlx-lm). Kept import-guarded so the rest
of the pipeline works without it.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("split_jsonl")
    ap.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--max-tokens", type=int, default=350)
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()

    try:
        from mlx_lm import load, generate
    except ImportError:
        raise SystemExit("mlx-lm not installed: .venv/bin/pip install mlx-lm")

    split_path = Path(args.split_jsonl)
    split_dir = split_path.parent
    split_manifest = json.loads((split_dir / "manifest.json").read_text())
    split_name = split_path.stem
    example_ids = split_manifest["splits"][split_name]["example_ids"]

    lines = split_path.read_text().splitlines()
    assert len(lines) == len(example_ids), "split/manifest mismatch"

    model, tokenizer = load(args.model, adapter_path=args.adapter)

    out_path = Path(args.out)
    with out_path.open("w") as out:
        for example_id, line in zip(example_ids, lines):
            messages = json.loads(line)["messages"][:-1]  # drop gold assistant turn
            prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
            answer = generate(model, tokenizer, prompt=prompt, max_tokens=args.max_tokens)
            out.write(json.dumps({"example_id": example_id, "answer": answer.strip()},
                                 ensure_ascii=False) + "\n")
            print(f"generated {example_id} ({len(answer.split())} words)")
    print(f"-> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
