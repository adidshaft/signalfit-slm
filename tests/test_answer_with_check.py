#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.answer_with_check import (  # noqa: E402
    ANSWER_SIDE_GATES,
    correction_errors,
    failed_checks,
    retry_messages,
    run_one,
)
from scripts.run_eval import load_examples  # noqa: E402


class AnswerWithCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.example = load_examples([ROOT / "eval/v1/cases"])["bind-v1-000002"]

    def test_failed_draft_has_specific_x1_and_s3_feedback_then_exactly_one_retry(self) -> None:
        # The draft's 104 bpm value is not allowed and is bound to the wrong RHR field.
        drafts = iter([
            "Your resting heart rate is 104 bpm, so it is above your baseline.",
            "Your resting heart rate is 62 bpm, so use a moderate session today.",
        ])
        calls = []

        def generate(messages):
            calls.append(messages)
            return next(drafts), 12.5, "test"

        generation, log = run_one(self.example, generate)
        self.assertEqual(len(calls), 2)
        self.assertTrue(log["retry_triggered"])
        self.assertEqual(generation["answer"], "Your resting heart rate is 62 bpm, so use a moderate session today.")
        self.assertIn("x1_grounding", log["failures"])
        self.assertIn("s3_field_binding", log["failures"])
        self.assertTrue(any("104 bpm" in error for error in log["correction_errors"]))
        correction_turn = calls[1][-1]["content"]
        self.assertIn("CHECK FAILURES", correction_turn)
        self.assertIn("104 bpm", correction_turn)
        self.assertEqual(set(log["draft_checks"]), set(ANSWER_SIDE_GATES))

    def test_passing_draft_skips_retry(self) -> None:
        calls = []

        def generate(messages):
            calls.append(messages)
            return "Your resting heart rate is 62 bpm; keep today moderate.", 4.0, "test"

        generation, log = run_one(self.example, generate)
        self.assertEqual(len(calls), 1)
        self.assertFalse(log["retry_triggered"])
        self.assertEqual(log["final_answer_source"], "draft")
        self.assertEqual(generation["answer"], "Your resting heart rate is 62 bpm; keep today moderate.")

    def test_error_rendering_uses_evaluator_details(self) -> None:
        failures = failed_checks({
            "x1_grounding": {"pass": False, "ungrounded": ["99 bpm"]},
            "s3_field_binding": {"pass": False, "errors": ["wrong field"]},
        })
        self.assertEqual(correction_errors(failures), [
            "x1_grounding: ungrounded number-and-unit values: ['99 bpm']",
            "s3_field_binding: wrong field",
        ])

    def test_retry_prompt_contains_original_draft_and_gate_errors(self) -> None:
        messages = retry_messages(self.example, "draft answer", ["s4: comparison is wrong"])
        self.assertEqual(messages[-2], {"role": "assistant", "content": "draft answer"})
        self.assertIn("s4: comparison is wrong", messages[-1]["content"])


if __name__ == "__main__":
    unittest.main()
