from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import judge_protocol_v2 as protocol


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = (
    ROOT
    / "data/checks/iteration14-judge-protocol-v2/systems/candidate/eval_report/judge_bundle.jsonl"
)
REPORT_PATH = (
    ROOT
    / "data/checks/iteration14-judge-protocol-v2/systems/candidate/eval_report/eval_report.json"
)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verdict(bundle: dict, judge: str, category_pass: bool, index: int) -> dict:
    criteria = {criterion_id: {"pass": True} for criterion_id in bundle["expected_criteria"]}
    if not category_pass:
        criterion_id = protocol.CATEGORY_CRITERIA[bundle["task_category"]][0]
        words = bundle["answer"].split()
        start = index % max(1, len(words) - 11)
        quote = " ".join(words[start:start + 12])
        criteria[criterion_id] = {
            "pass": False,
            "reason_code": "omitted_required",
            "explanation": (
                f"{quote} omits a required behavior for {bundle['example_id']}; "
                "this row-specific answer evidence establishes the criterion failure."
            ),
            "evidence": [{"kind": "answer_quote", "quote": quote}],
        }
    return {
        "example_id": bundle["example_id"],
        **{key: bundle[key] for key in protocol.VERSION_KEYS},
        "calibration_sha256": bundle["calibration_sha256"],
        "qualification_pack_sha256": bundle["qualification_pack_sha256"],
        "bundle_sha256": bundle["bundle_sha256"],
        "judge": judge,
        "criteria": criteria,
        "category_pass": category_pass,
    }


class MergeJudgmentsV2IntegrationTests(unittest.TestCase):
    def test_agreed_merge_preserves_v2_provenance_and_apply_accepts_it(self) -> None:
        bundles = [json.loads(line) for line in BUNDLE_PATH.read_text().splitlines()]
        bundle = bundles[0]
        source_report = json.loads(REPORT_PATH.read_text())

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            bundle_path = temp / "bundle.jsonl"
            pass_a_path = temp / "session-a.jsonl"
            pass_b_path = temp / "session-b.jsonl"
            merged_path = temp / "merged.jsonl"
            disagreements_path = temp / "disagreements.jsonl"
            trust_path = temp / "trusted_run_receipt.json"
            report_path = temp / "eval_report.json"
            judged_report_path = temp / "judged_report.json"

            write_jsonl(bundle_path, bundles)
            pass_a = {
                row["example_id"]: verdict(row, "judge-a", index < 100, index)
                for index, row in enumerate(bundles)
            }
            pass_b = {
                row["example_id"]: verdict(row, "judge-b", index < 100, index)
                for index, row in enumerate(bundles)
            }
            write_jsonl(pass_a_path, list(pass_a.values()))
            write_jsonl(pass_b_path, list(pass_b.values()))
            stats = protocol.agreement_stats(pass_a, pass_b)
            trusted_stats = {**stats, **protocol.trust_result(stats)}
            trust = {
                "run_id": "test-paired-run",
                "judge_protocol_version": protocol.JUDGE_PROTOCOL_VERSION,
                "qualification_pack_sha256": protocol.qualification_pack_sha256(),
                "overall_trusted": True,
                "systems": {"candidate": trusted_stats, "ft_v2": trusted_stats},
                "manifest_sha256": "0" * 64,
                "trust_report_sha256": "1" * 64,
                "qualification_receipt_sha256": {
                    "session-a": "2" * 64,
                    "session-b": "3" * 64,
                },
                "source_bundle_sha256": {
                    "candidate": file_sha(bundle_path),
                    "ft_v2": "4" * 64,
                },
                "primary_output_sha256": {
                    "candidate": {
                        "session-a": file_sha(pass_a_path),
                        "session-b": file_sha(pass_b_path),
                    },
                    "ft_v2": {"session-a": "5" * 64, "session-b": "6" * 64},
                },
            }
            trust["receipt_sha256"] = protocol.sha256_json(trust)
            trust_path.write_text(json.dumps(trust))

            merge = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/merge_judgments.py"),
                    "--pass-a", str(pass_a_path),
                    "--pass-b", str(pass_b_path),
                    "--bundle", str(bundle_path),
                    "--out", str(merged_path),
                    "--disagreements", str(disagreements_path),
                    "--trust-receipt", str(trust_path),
                    "--system", "candidate",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(merge.returncode, 0, merge.stderr or merge.stdout)
            merged_rows = [json.loads(line) for line in merged_path.read_text().splitlines()]
            self.assertEqual(len(merged_rows), 200)
            self.assertTrue(all(
                row["qualification_pack_sha256"] == bundle["qualification_pack_sha256"]
                for row in merged_rows
            ))
            by_bundle = {row["example_id"]: row for row in bundles}
            for row in merged_rows:
                protocol.validate_verdict(row, by_bundle[row["example_id"]], "merged")

            report_path.write_text(json.dumps({
                "summary": {
                    **{key: bundle[key] for key in protocol.VERSION_KEYS},
                    "calibration_sha256": bundle["calibration_sha256"],
                    "qualification_pack_sha256": bundle["qualification_pack_sha256"],
                    "deterministic_pass_rate": source_report["summary"]["deterministic_pass_rate"],
                    "by_gate": {},
                },
                "results": source_report["results"],
            }))
            apply = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/apply_judge.py"),
                    "--report", str(report_path),
                    "--verdicts", str(merged_path),
                    "--bundle", str(bundle_path),
                    "--out", str(judged_report_path),
                    "--trust-receipt", str(trust_path),
                    "--system", "candidate",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(apply.returncode, 0, apply.stderr or apply.stdout)
            self.assertTrue(judged_report_path.exists())


if __name__ == "__main__":
    unittest.main()
