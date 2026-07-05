#!/usr/bin/env python3
"""Split a prepared JSONL (+manifest) into train/valid/eval per docs/finetuning_format.md.

Usage:
    .venv/bin/python scripts/split_dataset.py data/ft_v0/all.jsonl --out-dir data/ft_v0 [--valid-frac 0.1] [--seed 17]

Policy:
  - is_locked_eval -> eval.jsonl, never train/valid.
  - Remaining examples are split BY PERSONA (a persona never appears in both
    train and valid), stratified as evenly as the persona grouping allows.
  - Deterministic given --seed. Writes manifest.json with counts, per-file
    sha256, and source example ids per split; asserts train ∩ eval = ∅.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--valid-frac", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=17)
    args = ap.parse_args()

    src = Path(args.jsonl)
    manifest = json.loads(src.with_suffix(src.suffix + ".manifest.json").read_text())
    lines = src.read_text().splitlines()
    assert len(lines) == manifest["count"], "manifest/count mismatch"

    entries = manifest["examples"]
    eval_entries = [e for e in entries if e["is_locked_eval"]]
    rest = [e for e in entries if not e["is_locked_eval"]]

    by_persona: dict[str, list[dict]] = defaultdict(list)
    for e in rest:
        by_persona[e["persona_id"] or e["example_id"]].append(e)

    personas = sorted(by_persona)
    random.Random(args.seed).shuffle(personas)
    target_valid = round(len(rest) * args.valid_frac)
    valid_entries: list[dict] = []
    for persona in personas:
        if len(valid_entries) >= target_valid:
            break
        valid_entries.extend(by_persona[persona])
    valid_ids = {e["example_id"] for e in valid_entries}
    train_entries = [e for e in rest if e["example_id"] not in valid_ids]

    train_ids = {e["example_id"] for e in train_entries}
    eval_ids = {e["example_id"] for e in eval_entries}
    assert not (train_ids & eval_ids), "train/eval contamination"
    assert not (valid_ids & eval_ids), "valid/eval contamination"

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    split_manifest = {"seed": args.seed, "valid_frac": args.valid_frac,
                      "source": str(src), "source_sha256": sha256_of(src), "splits": {}}
    for name, split in (("train", train_entries), ("valid", valid_entries), ("eval", eval_entries)):
        path = out_dir / f"{name}.jsonl"
        path.write_text("".join(lines[e["line"] - 1] + "\n" for e in split))
        cats: dict[str, int] = defaultdict(int)
        for e in split:
            cats[e["task_category"]] += 1
        split_manifest["splits"][name] = {
            "count": len(split),
            "sha256": sha256_of(path),
            "by_category": dict(sorted(cats.items())),
            "example_ids": [e["example_id"] for e in split],
        }
        print(f"{name}: {len(split)} -> {path}")

    (out_dir / "manifest.json").write_text(json.dumps(split_manifest, indent=2) + "\n")
    print(f"manifest -> {out_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
