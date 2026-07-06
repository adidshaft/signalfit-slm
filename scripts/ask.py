#!/usr/bin/env python3
"""Ask the fine-tuned SignalFit-SLM a question against a context JSON.

Usage:
    .venv/bin/python scripts/ask.py <context-or-example.json> "your question"
    .venv/bin/python scripts/ask.py --random "should I train hard today?"

Accepts either a bare sf-context-1 JSON file or a full training-example file
(the context is extracted). --random picks a random curated example's context.
The adapter defaults to the latest run (ft_v2).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_dataset import SYSTEM_PROMPT, model_input_context  # noqa: E402
from run_eval import NUM_UNIT  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("context", nargs="?", help="context or training-example JSON file")
    ap.add_argument("question")
    ap.add_argument("--random", action="store_true", help="use a random curated context")
    ap.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--adapter", default=str(REPO / "models/adapters/ft_v2_qwen2.5-1.5b"))
    ap.add_argument("--max-tokens", type=int, default=300)
    args = ap.parse_args()

    if args.random:
        pool = list((REPO / "data/synthetic/curated/agent_v1").glob("*.json"))
        path = random.choice(pool)
        print(f"[context: {path.name}]")
    elif args.context:
        path = Path(args.context)
    else:
        raise SystemExit("provide a context file or --random")

    doc = json.loads(path.read_text())
    ctx = model_input_context(doc["context"] if "context" in doc else doc)
    ctx_json = json.dumps(ctx, separators=(",", ":"), sort_keys=True)

    from mlx_lm import load, generate
    model, tok = load(args.model, adapter_path=args.adapter)
    prompt = tok.apply_chat_template(
        [{"role": "system", "content": SYSTEM_PROMPT},
         {"role": "user", "content": f"CONTEXT:\n{ctx_json}\n\nQUESTION: {args.question}"}],
        add_generation_prompt=True)
    answer = generate(model, tok, prompt=prompt, max_tokens=args.max_tokens)
    print(answer.strip())

    # grounding check on the fly — flag any number not in the context contract
    allowed = [a["value"] for a in ctx.get("allowed_numbers", [])]
    bad = [m.group(0) for m in NUM_UNIT.finditer(answer)
           if not any(abs(v - float(m.group(1))) <= 1.0 for v in allowed)]
    if bad:
        print(f"\n[grounding warning: {bad} not in context allowed_numbers]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
