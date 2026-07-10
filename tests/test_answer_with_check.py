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
    serving_length_check,
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
            "x4_followups": {"pass": False, "questions": 2},
            "x6_length": {"pass": False, "words": 81, "bounds": [0, 80], "policy": "refusal_shaped"},
            "s3_field_binding": {"pass": False, "errors": ["wrong field"]},
        })
        self.assertEqual(correction_errors(failures), [
            "x1_grounding: ungrounded number-and-unit values: ['99 bpm']",
            "x4_followups: use at most one follow-up question (found 2)",
            "x6_length: response is 81 words; keep it at or below 80 words (refusal_shaped serving policy)",
            "s3_field_binding: wrong field",
        ])

    def test_serving_length_proxy_is_conservative_without_expected_action(self) -> None:
        refusal = "I can't help with that. " + "safe " * 76
        ordinary = "Consider an easy session today. " + "detail " * 181
        self.assertEqual(serving_length_check(refusal)["bounds"], [0, 80])
        self.assertFalse(serving_length_check(refusal)["pass"])
        self.assertEqual(serving_length_check(ordinary)["bounds"], [0, 190])
        self.assertTrue(serving_length_check(ordinary)["pass"])

    def test_x4_and_x6_failures_trigger_exactly_one_retry(self) -> None:
        draft = "I can't help with that. " + "safe " * 76 + "What else? Why?"
        calls = []

        def generate(messages):
            calls.append(messages)
            return (draft if len(calls) == 1 else "I can't help with that request. A qualified clinician can help you safely.", 1.0, "test")

        generation, log = run_one(self.example, generate)
        self.assertEqual(len(calls), 2)
        self.assertTrue(log["retry_triggered"])
        self.assertIn("x4_followups", log["failures"])
        self.assertIn("x6_length", log["failures"])
        self.assertEqual(generation["answer"], "I can't help with that request. A qualified clinician can help you safely.")

    def test_retry_prompt_contains_original_draft_and_gate_errors(self) -> None:
        messages = retry_messages(self.example, "draft answer", ["s4: comparison is wrong"])
        self.assertEqual(messages[-2], {"role": "assistant", "content": "draft answer"})
        self.assertIn("s4: comparison is wrong", messages[-1]["content"])


if __name__ == "__main__":
    unittest.main()
