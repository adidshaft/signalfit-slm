#!/usr/bin/env python3
from __future__ import annotations

import unittest

from scripts.summarize_retry_run import summarize


class SummarizeRetryRunTests(unittest.TestCase):
    def test_latency_and_protected_flip(self) -> None:
        logs = {
            "a": {
                "retry_triggered": False,
                "draft_latency_ms": 10,
                "retry_latency_ms": None,
                "failures": {},
                "final_answer_side_pass": True,
            },
            "b": {
                "retry_triggered": True,
                "draft_latency_ms": 20,
                "retry_latency_ms": 30,
                "failures": {"s4": {"pass": False}},
                "final_answer_side_pass": True,
            },
        }
        previous = {
            "a": {"deterministic_pass": True, "checks": {}},
            "b": {"deterministic_pass": False, "checks": {}},
        }
        current = {
            "a": {"deterministic_pass": True, "checks": {}},
            "b": {
                "deterministic_pass": True,
                "checks": {"s4": {"pass": True}},
            },
        }

        result = summarize(logs, current, previous, ["b"])

        self.assertEqual(result["retry_count"], 1)
        self.assertEqual(result["retry_rate"], 0.5)
        self.assertEqual(result["latency"]["total_system_all_cases"]["median_ms"], 30.0)
        self.assertTrue(result["protected_cases"]["b"]["flipped_fail_to_pass"])
        self.assertEqual(result["protected_cases"]["b"]["draft_failed_checks"], ["s4"])

    def test_coverage_mismatch_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "coverage differ"):
            summarize({}, {"a": {}}, {"a": {}}, [])


if __name__ == "__main__":
    unittest.main()
