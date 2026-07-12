#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.generate_local_teacher import (  # noqa: E402
    action_for,
    assemble_example,
    gate_clean,
)
from scripts.make_context_specs import main as make_specs_main  # noqa: E402


class LocalTeacherPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import json
        # a real deterministic spec via the same simulator the seed set uses
        out = ROOT / "data/synthetic/raw/_test_teacher_specs"
        argv = [
            "--seed", "999", "--prefix", "tt", "--out", str(out / "specs"),
            "--chunk-size", "10", "--plan",
            json.dumps({"sleep_coaching": 2, "safety_triage": 2}),
        ]
        old = sys.argv
        sys.argv = ["make_context_specs.py"] + argv
        try:
            make_specs_main()
        finally:
            sys.argv = old
        cls.specs = []
        for chunk in sorted((out / "specs").glob("chunk_*.json")):
            cls.specs.extend(json.loads(chunk.read_text()))
        cls._artifact = out

    @classmethod
    def tearDownClass(cls) -> None:
        import shutil
        shutil.rmtree(cls._artifact, ignore_errors=True)

    def test_action_mapping_is_gate_correct(self) -> None:
        self.assertEqual(action_for("safety_triage"), "triage")
        self.assertEqual(action_for("refusal_or_redirect"), "refuse")
        self.assertEqual(action_for("insufficient_data_followup"), "followup")
        self.assertEqual(action_for("sleep_coaching"), "answer_with_caveat")

    def test_grounded_directional_answer_is_gate_clean(self) -> None:
        spec = next(s for s in self.specs if s["category"] == "sleep_coaching")
        answer = (
            "Keep today's plan steady and make small, reversible adjustments "
            "rather than large ones. Watch the multi-day trend against your own "
            "usual range before changing anything, and check in again if how you "
            "feel keeps drifting from what the numbers say over the coming days."
        )
        ok, failed = gate_clean(assemble_example(spec, "How am I doing?", answer))
        self.assertTrue(ok, failed)

    def test_invented_number_is_quarantined(self) -> None:
        spec = self.specs[0]
        answer = "Your HRV is 999 ms, far above your 12 ms baseline, so add 5 hard sessions."
        ok, failed = gate_clean(assemble_example(spec, "How am I doing?", answer))
        self.assertFalse(ok)
        self.assertIn("x1_grounding", failed)

    def test_assembled_example_carries_required_schema_fields(self) -> None:
        spec = next(s for s in self.specs if s["category"] == "safety_triage")
        ex = assemble_example(spec, "My chest hurts, should I run?", "Please seek prompt medical care.")
        self.assertEqual(ex["labels"]["safety_class"], "medical_red_flag")
        self.assertIn("generation", ex)
        self.assertEqual(ex["target_response"]["expected_action"], "triage")


if __name__ == "__main__":
    unittest.main()
