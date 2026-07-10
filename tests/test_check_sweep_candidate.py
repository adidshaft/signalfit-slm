#!/usr/bin/env python3
from __future__ import annotations

import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.check_sweep_candidate import SAFETY_GATES, main


def report(*, judged: bool) -> dict:
    results = [
        {"example_id": "protected", "deterministic_pass": True},
        {"example_id": "unprotected", "deterministic_pass": False},
    ]
    if judged:
        results[0]["overall_pass"] = True
        results[1]["overall_pass"] = False
    return {
        "summary": {
            "gate_version": "sf-gates-test",
            "rubric_version": "rubric-test",
            "deterministic_pass_rate": 0.5,
            "by_gate": {
                gate: {"n": 2, "pass": 2} for gate in SAFETY_GATES
            },
        },
        "results": results,
    }


class SweepCandidateCLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline = report(judged=True)
        self.candidate = report(judged=False)

    def run_cli(self, baseline: dict, candidate: dict) -> tuple[int, dict]:
        with tempfile.TemporaryDirectory() as directory:
            baseline_path = Path(directory) / "baseline.json"
            candidate_path = Path(directory) / "candidate.json"
            baseline_path.write_text(json.dumps(baseline))
            candidate_path.write_text(json.dumps(candidate))
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--baseline",
                        str(baseline_path),
                        "--candidate",
                        str(candidate_path),
                    ]
                )
        return exit_code, json.loads(stdout.getvalue())

    def test_survivor(self) -> None:
        exit_code, result = self.run_cli(self.baseline, self.candidate)

        self.assertEqual(exit_code, 0)
        self.assertTrue(result["survivor"])
        self.assertTrue(all(gate["pass"] for gate in result["gate_comparisons"].values()))
        self.assertEqual(result["protect_count"], 1)
        self.assertEqual(result["protect_failures"], [])

    def test_aggregate_rejection(self) -> None:
        self.candidate["summary"]["deterministic_pass_rate"] = 0.49

        exit_code, result = self.run_cli(self.baseline, self.candidate)

        self.assertEqual(exit_code, 1)
        self.assertFalse(result["survivor"])
        self.assertFalse(result["gate_comparisons"]["deterministic_pass_rate"]["pass"])

    def test_safety_rejection(self) -> None:
        self.candidate["summary"]["by_gate"][SAFETY_GATES[1]]["pass"] = 1

        exit_code, result = self.run_cli(self.baseline, self.candidate)

        self.assertEqual(exit_code, 1)
        self.assertFalse(result["gate_comparisons"][SAFETY_GATES[1]]["pass"])
        self.assertEqual(result["protect_failures"], [])

    def test_protect_rejection(self) -> None:
        self.candidate["results"][0]["deterministic_pass"] = False

        exit_code, result = self.run_cli(self.baseline, self.candidate)

        self.assertEqual(exit_code, 1)
        self.assertEqual(result["protect_failures"], ["protected"])

    def test_version_and_coverage_errors(self) -> None:
        version_candidate = copy.deepcopy(self.candidate)
        version_candidate["summary"]["gate_version"] = "sf-gates-other"
        coverage_candidate = copy.deepcopy(self.candidate)
        coverage_candidate["results"].pop()

        for candidate, expected_error in (
            (version_candidate, "gate_version mismatch"),
            (coverage_candidate, "example ID coverage mismatch"),
        ):
            with self.subTest(expected_error=expected_error):
                exit_code, result = self.run_cli(self.baseline, candidate)
                self.assertEqual(exit_code, 2)
                self.assertFalse(result["comparable"])
                self.assertIn(expected_error, result["errors"])


if __name__ == "__main__":
    unittest.main()
