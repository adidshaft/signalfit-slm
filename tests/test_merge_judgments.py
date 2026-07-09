#!/usr/bin/env python3
from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.merge_judgments import canonical_criterion_id, canonicalize_criteria


class CriterionCanonicalizationTests(unittest.TestCase):
    def test_cross_cutting_aliases_collapse_to_rubric_ids(self) -> None:
        aliases = {
            "X1 grounding": "X1",
            "X2 hedging": "X2",
            "X3 personal-vs-population": "X3",
            "X4 followup-budget": "X4",
            "X5 no-brands": "X5",
            "X6 shape": "X6",
            "X7 safety-precedence": "X7",
        }
        for raw, expected in aliases.items():
            self.assertEqual(canonical_criterion_id(raw), expected)
        self.assertEqual(canonical_criterion_id("S1"), "S1")

    def test_alias_collision_keeps_strict_failure(self) -> None:
        result = canonicalize_criteria({
            "X1": {"pass": True, "reason": "short-id pass"},
            "X1 grounding": {"pass": False, "reason": "long-id failure"},
            "D1": {"pass": True, "reason": "category pass"},
        })
        self.assertEqual(set(result), {"X1", "D1"})
        self.assertFalse(result["X1"]["pass"])
        self.assertEqual(result["X1"]["reason"], "long-id failure")


if __name__ == "__main__":
    unittest.main()
