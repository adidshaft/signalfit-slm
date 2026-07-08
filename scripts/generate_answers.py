#!/usr/bin/env python3
"""Generate model answers for a prepared split or example dirs (post-training).

Split mode (chat JSONL + sidecar manifest for example_ids):
    .venv/bin/python scripts/generate_answers.py data/ft_v0/eval.jsonl \
        --model Qwen/Qwen2.5-1.5B-Instruct \
        --adapter models/adapters/ft_v0_qwen2.5-1.5b \
        -o data/ft_v0/eval_generations.jsonl

Examples mode (directories of training-example JSONs, e.g. a frozen eval
suite slice — prompt built exactly like training via prepare_dataset):
    .venv/bin/python scripts/generate_answers.py \
        --examples eval/v1/cases/adversarial eval/v1/cases/binding \
        --adapter models/adapters/ft_v2_qwen2.5-1.5b \
        -o data/ft_v2/eval_suite_generations.jsonl

Writes {"example_id", "answer"} lines for scripts/run_eval.py.
Requires mlx-lm (.venv/bin/pip install mlx-lm). Kept import-guarded so the rest
of the pipeline works without it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_dataset import SYSTEM_PROMPT, model_input_context  # noqa: E402


def split_prompts(split_jsonl: str):
    """(example_id, messages) pairs from a chat split + its sidecar manifest."""
    split_path = Path(split_jsonl)
    split_manifest = json.loads((split_path.parent / "manifest.json").read_text())
    example_ids = split_manifest["splits"][split_path.stem]["example_ids"]
    lines = split_path.read_text().splitlines()
    assert len(lines) == len(example_ids), "split/manifest mismatch"
    for example_id, line in zip(example_ids, lines):
        yield example_id, json.loads(line)["messages"][:-1]  # drop gold assistant turn


def example_prompts(dirs: list[str]):
    for d in dirs:
        for path in sorted(Path(d).rglob("*.json")):
            ex = json.loads(path.read_text())
            ctx_json = json.dumps(model_input_context(ex["context"]),
                                  separators=(",", ":"), sort_keys=True, ensure_ascii=False)
            question = ex["context"]["request"]["user_question"]
            yield ex["example_id"], [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"CONTEXT:\n{ctx_json}\n\nQUESTION: {question}"},
            ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("split_jsonl", nargs="?")
    ap.add_argument("--examples", nargs="+", help="dirs of training-example JSONs instead of a split")
    ap.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--max-tokens", type=int, default=350)
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()
    if bool(args.split_jsonl) == bool(args.examples):
        ap.error("provide either a split JSONL or --examples dirs (not both)")

    try:
        from mlx_lm import load, generate
    except ImportError:
        raise SystemExit("mlx-lm not installed: .venv/bin/pip install mlx-lm")

    prompts = example_prompts(args.examples) if args.examples else split_prompts(args.split_jsonl)
    model, tokenizer = load(args.model, adapter_path=args.adapter)

    out_path = Path(args.out)
    with out_path.open("w") as out:
        for example_id, messages in prompts:
            prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
            answer = generate(model, tokenizer, prompt=prompt, max_tokens=args.max_tokens)
            out.write(json.dumps({"example_id": example_id, "answer": answer.strip()},
                                 ensure_ascii=False) + "\n")
            print(f"generated {example_id} ({len(answer.split())} words)")
    print(f"-> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
