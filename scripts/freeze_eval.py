#!/usr/bin/env python3
"""Freeze / verify a versioned eval suite under eval/<version>/.

Build (copies case files, writes hashed manifest, runs contamination check):
    .venv/bin/python scripts/freeze_eval.py build --version v1

Verify (re-hash every frozen case against the manifest + re-run contamination;
CI-style guard, exit 1 on any drift):
    .venv/bin/python scripts/freeze_eval.py check --version v1

A frozen suite is append-only: new slices (subdirectories of cases/) may be
added with `build` (existing files must hash-match — they are never rewritten),
but a case that has ever been frozen must never change or disappear. Changing
an existing case means bumping the suite version so scores stay comparable.

Contamination rule: no example_id in the suite may appear in any training or
validation split of any data/ft_*/manifest.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def suite_cases(suite_dir: Path) -> list[Path]:
    return sorted((suite_dir / "cases").rglob("*.json"))


def train_valid_ids() -> dict[str, str]:
    """example_id -> split manifest that contains it (train/valid only)."""
    ids: dict[str, str] = {}
    for manifest_path in sorted(REPO.glob("data/ft_*/manifest.json")):
        manifest = json.loads(manifest_path.read_text())
        for split_name, split in manifest.get("splits", {}).items():
            if split_name == "eval":
                continue
            for example_id in split.get("example_ids", []):
                ids[example_id] = f"{manifest_path}:{split_name}"
    return ids


def contamination_errors(case_files: list[Path]) -> list[str]:
    contaminated = train_valid_ids()
    errors = []
    for path in case_files:
        example_id = json.loads(path.read_text())["example_id"]
        if example_id in contaminated:
            errors.append(f"{example_id} ({path.name}) appears in {contaminated[example_id]}")
    return errors


def build(version: str) -> int:
    suite_dir = REPO / "eval" / version
    case_files = suite_cases(suite_dir)
    if not case_files:
        sys.exit(f"no case files under {suite_dir}/cases/ — add slices first")

    manifest_path = suite_dir / "manifest.json"
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else None

    entries, seen_ids, errors = [], set(), []
    for path in case_files:
        example = json.loads(path.read_text())
        example_id = example["example_id"]
        if example_id in seen_ids:
            errors.append(f"duplicate example_id {example_id}")
        seen_ids.add(example_id)
        entries.append({
            "example_id": example_id,
            "slice": path.parent.name,
            "task_category": example["task_category"],
            "case_type": example["case_type"],
            "expected_action": example["target_response"]["expected_action"],
            "file": str(path.relative_to(suite_dir)),
            "sha256": sha256(path),
        })

    if previous:  # append-only: previously frozen cases must be byte-identical
        old = {e["file"]: e["sha256"] for e in previous["cases"]}
        new = {e["file"]: e["sha256"] for e in entries}
        for file, digest in old.items():
            if file not in new:
                errors.append(f"frozen case removed: {file}")
            elif new[file] != digest:
                errors.append(f"frozen case modified: {file} (bump the suite version instead)")

    errors += contamination_errors(case_files)
    if errors:
        print("FREEZE REFUSED:\n  " + "\n  ".join(errors))
        return 1

    by_slice: dict[str, int] = {}
    for e in entries:
        by_slice[e["slice"]] = by_slice.get(e["slice"], 0) + 1
    manifest = {
        "suite": f"sf-eval-{version}",
        "count": len(entries),
        "by_slice": by_slice,
        "cases": entries,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"froze {len(entries)} cases ({by_slice}) -> {manifest_path}")
    return 0


def check(version: str) -> int:
    suite_dir = REPO / "eval" / version
    manifest_path = suite_dir / "manifest.json"
    if not manifest_path.exists():
        sys.exit(f"no manifest at {manifest_path} — run build first")
    manifest = json.loads(manifest_path.read_text())

    errors = []
    for entry in manifest["cases"]:
        path = suite_dir / entry["file"]
        if not path.exists():
            errors.append(f"missing frozen case: {entry['file']}")
        elif sha256(path) != entry["sha256"]:
            errors.append(f"frozen case drifted: {entry['file']}")
    on_disk = {str(p.relative_to(suite_dir)) for p in suite_cases(suite_dir)}
    unfrozen = on_disk - {e["file"] for e in manifest["cases"]}
    if unfrozen:
        errors.append(f"unfrozen case files present (run build): {sorted(unfrozen)}")
    errors += contamination_errors(suite_cases(suite_dir))

    if errors:
        print(f"SUITE {manifest['suite']} FAILED:\n  " + "\n  ".join(errors))
        return 1
    print(f"suite {manifest['suite']} OK: {manifest['count']} cases, hashes match, no train/valid contamination")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["build", "check"])
    ap.add_argument("--version", default="v1")
    args = ap.parse_args()
    return build(args.version) if args.command == "build" else check(args.version)


if __name__ == "__main__":
    raise SystemExit(main())
