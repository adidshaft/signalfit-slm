#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts import judge_protocol_v2 as protocol
from scripts.judge_v2_orchestrator import (
    build_run,
    qualify,
    qualification_case_bundle,
    score_exact_gold,
    unlock,
    validate_shard,
    write_shard_agreement_if_ready,
)


def pointer_get(document, pointer: str):
    value = document
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def golden_verdict(bundle: dict, qualification_id: str, judge: str = "judge-a") -> dict:
    gold = protocol.load_qualification_gold()[qualification_id]
    criteria = {}
    for criterion_id, passed in gold["criteria"].items():
        if passed:
            criteria[criterion_id] = {"pass": True}
            continue
        failure = gold["failures"][criterion_id]
        evidence = []
        quotes = failure["allowed_answer_quotes"][:failure["minimum_quotes"]]
        pointers = failure["allowed_context_pointers"][:failure["minimum_pointers"]]
        evidence.extend({"kind": "answer_quote", "quote": quote} for quote in quotes)
        evidence.extend({
            "kind": "context_pointer",
            "pointer": pointer,
            "observed_value": pointer_get({"context": bundle["context"]}, pointer),
        } for pointer in pointers)
        cited = " ".join(quotes + pointers)
        explanation = (
            f"{cited} specifically demonstrates {qualification_id} {criterion_id}; "
            "the cited answer and context evidence establish this failure."
        )
        criteria[criterion_id] = {
            "pass": False,
            "reason_code": failure["allowed_reason_codes"][0],
            "explanation": explanation,
            "evidence": evidence,
        }
    return {
        "example_id": bundle["example_id"],
        **{key: bundle[key] for key in protocol.VERSION_KEYS},
        "calibration_sha256": bundle["calibration_sha256"],
        "qualification_pack_sha256": bundle["qualification_pack_sha256"],
        "bundle_sha256": bundle["bundle_sha256"],
        "run_id": bundle["run_id"],
        "session_id": bundle["session_id"],
        "shard_id": bundle["shard_id"],
        "judge": judge,
        "criteria": criteria,
        "category_pass": gold["category_pass"],
    }


class JudgeProtocolV2Tests(unittest.TestCase):
    def qualification_fixture(self):
        cases = protocol.load_qualification_cases()
        bundles = {
            qid: qualification_case_bundle(
                case, run_id="test-run", session="session-a", shard_id="qualification"
            )
            for qid, case in cases.items()
        }
        verdicts = {qid: golden_verdict(bundle, qid) for qid, bundle in bundles.items()}
        by_blind = {bundle["example_id"]: bundle for bundle in bundles.values()}
        verdict_by_blind = {verdict["example_id"]: verdict for verdict in verdicts.values()}
        crosswalk = {bundle["example_id"]: qid for qid, bundle in bundles.items()}
        return by_blind, verdict_by_blind, crosswalk

    def test_pack_has_exact_complete_bidirectional_coverage(self) -> None:
        cases = protocol.load_qualification_cases()
        gold = protocol.load_qualification_gold()
        self.assertEqual(len(cases), 26)
        self.assertEqual(set(cases), set(gold))
        coverage = {}
        for qid, case in cases.items():
            self.assertEqual(case["expected_criteria"], list(protocol.expected_criteria(case["task_category"])))
            false_ids = {cid for cid, passed in gold[qid]["criteria"].items() if not passed}
            self.assertEqual(false_ids, set(gold[qid]["failures"]))
            category_ids = protocol.CATEGORY_CRITERIA[case["task_category"]]
            self.assertEqual(gold[qid]["category_pass"], all(gold[qid]["criteria"][cid] for cid in category_ids))
            for cid, passed in gold[qid]["criteria"].items():
                coverage.setdefault(cid, set()).add(passed)
        self.assertEqual(len(coverage), 37)
        self.assertTrue(all(values == {False, True} for values in coverage.values()))

    def test_perfect_qualification_scores_and_one_flip_fails(self) -> None:
        bundles, verdicts, crosswalk = self.qualification_fixture()
        score = score_exact_gold(verdicts, bundles, crosswalk, "test")
        self.assertEqual(score["decision_correct"], score["decision_total"])
        broken = copy.deepcopy(verdicts)
        first = next(iter(broken.values()))
        first_id = next(iter(first["criteria"]))
        first["criteria"][first_id]["pass"] = not first["criteria"][first_id]["pass"]
        with self.assertRaises(ValueError):
            score_exact_gold(broken, bundles, crosswalk, "test")

    def test_failure_evidence_is_exact_and_bound(self) -> None:
        bundles, verdicts, _ = self.qualification_fixture()
        protocol.validate_batch(verdicts, bundles, "test")
        failed = next(v for v in verdicts.values() if any(not c["pass"] for c in v["criteria"].values()))
        cid = next(cid for cid, result in failed["criteria"].items() if not result["pass"])
        broken = copy.deepcopy(failed)
        anchor = broken["criteria"][cid]["evidence"][0]
        if anchor["kind"] == "answer_quote":
            anchor["quote"] = "not present in the answer"
        else:
            anchor["pointer"] = "/context/not_present"
        with self.assertRaises(ValueError):
            protocol.validate_verdict(broken, bundles[broken["example_id"]], "test")

    def test_empty_context_pointer_is_rejected(self) -> None:
        bundles, verdicts, _ = self.qualification_fixture()
        failed = next(
            verdict for verdict in verdicts.values()
            if any(
                anchor["kind"] == "context_pointer"
                for result in verdict["criteria"].values() if not result["pass"]
                for anchor in result["evidence"]
            )
        )
        broken = copy.deepcopy(failed)
        criterion = next(
            result for result in broken["criteria"].values()
            if not result["pass"] and any(a["kind"] == "context_pointer" for a in result["evidence"])
        )
        pointer = next(a for a in criterion["evidence"] if a["kind"] == "context_pointer")
        pointer["pointer"] = ""
        with self.assertRaisesRegex(ValueError, "below /context"):
            protocol.validate_verdict(broken, bundles[broken["example_id"]], "test")

    def test_duplicate_evidence_anchor_is_rejected(self) -> None:
        bundles, verdicts, _ = self.qualification_fixture()
        failed = next(
            verdict for verdict in verdicts.values()
            if any(not result["pass"] and len(result["evidence"]) < 3 for result in verdict["criteria"].values())
        )
        broken = copy.deepcopy(failed)
        result = next(result for result in broken["criteria"].values() if not result["pass"] and len(result["evidence"]) < 3)
        result["evidence"].append(copy.deepcopy(result["evidence"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate anchors"):
            protocol.validate_verdict(broken, bundles[broken["example_id"]], "test")

    def test_qualification_rejects_schema_valid_non_gold_evidence(self) -> None:
        bundles, verdicts, crosswalk = self.qualification_fixture()
        broken = copy.deepcopy(verdicts)
        for blind_id, verdict in broken.items():
            qid = crosswalk[blind_id]
            gold = protocol.load_qualification_gold()[qid]
            for criterion_id, result in verdict["criteria"].items():
                if result["pass"]:
                    continue
                allowed = set(gold["failures"][criterion_id]["allowed_answer_quotes"])
                words = bundles[blind_id]["answer"].split()
                replacement = next(
                    (" ".join(words[index:index + 3]) for index in range(len(words) - 2)
                     if " ".join(words[index:index + 3]) not in allowed),
                    None,
                )
                quote = next((a for a in result["evidence"] if a["kind"] == "answer_quote"), None)
                if quote is None or replacement is None:
                    continue
                old_quote = quote["quote"]
                quote["quote"] = replacement
                result["explanation"] = result["explanation"].replace(old_quote, replacement)
                protocol.validate_batch(broken, bundles, "schema-valid")
                with self.assertRaisesRegex(ValueError, "answer quote misses gold"):
                    score_exact_gold(broken, bundles, crosswalk, "gold-bound")
                return
        self.fail("fixture had no replaceable answer quote")

    def test_repeated_generic_failure_and_all_fail_collapse_are_rejected(self) -> None:
        bundles, verdicts, _ = self.qualification_fixture()
        failures = []
        for verdict in verdicts.values():
            for cid, result in verdict["criteria"].items():
                if not result["pass"]:
                    failures.append((verdict, cid, result))
        template = failures[0][2]
        changed = copy.deepcopy(verdicts)
        touched = 0
        for verdict in changed.values():
            for cid, result in verdict["criteria"].items():
                if cid == "X1" and not result["pass"] and touched < 3:
                    quote = next((a for a in result["evidence"] if a["kind"] == "answer_quote"), None)
                    if quote is None:
                        continue
                    pointers = " ".join(
                        a["pointer"] for a in result["evidence"] if a["kind"] == "context_pointer"
                    )
                    result["explanation"] = (
                        f"{quote['quote']} {pointers} are cited evidence and this same generic template "
                        "states that the criterion fails for the answer."
                    )
                    touched += 1
                    break
        with self.assertRaisesRegex(ValueError, "repeated generic"):
            protocol.validate_batch(changed, bundles, "test")

    def test_constant_margins_have_undefined_kappa_and_fail_trust(self) -> None:
        row = {"category_pass": True, "criteria": {"X1": {"pass": True}}}
        a = {str(i): copy.deepcopy(row) for i in range(10)}
        b = {str(i): copy.deepcopy(row) for i in range(10)}
        stats = protocol.agreement_stats(a, b)
        self.assertIsNone(stats["cohen_kappa"])
        self.assertFalse(protocol.trust_result(stats)["trusted"])

    def test_trust_boundaries_are_inclusive(self) -> None:
        stats = {"category_agreement_rate": 0.80, "cohen_kappa": 0.60, "pass_rate_gap": 0.10}
        self.assertTrue(protocol.trust_result(stats)["trusted"])
        for key, value in (("category_agreement_rate", 0.7999), ("cohen_kappa", 0.5999), ("pass_rate_gap", 0.1001)):
            broken = dict(stats)
            broken[key] = value
            self.assertFalse(protocol.trust_result(broken)["trusted"])

    def test_unrounded_kappa_below_threshold_cannot_round_up_to_pass(self) -> None:
        a = {}
        b = {}
        categories = (
            [(True, True)] * 79
            + [(False, False)] * 81
            + [(True, False)] * 20
            + [(False, True)] * 20
        )
        for index, (a_pass, b_pass) in enumerate(categories):
            a[str(index)] = {"category_pass": a_pass, "criteria": {"X1": {"pass": a_pass}}}
            b[str(index)] = {"category_pass": b_pass, "criteria": {"X1": {"pass": b_pass}}}
        stats = protocol.agreement_stats(a, b)
        self.assertEqual(stats["cohen_kappa"], 0.6)
        self.assertLess(stats["raw_cohen_kappa"], 0.6)
        self.assertFalse(protocol.trust_result(stats)["trusted"])

    def test_trust_receipt_reconstructs_two_200_row_system_statistics(self) -> None:
        a = {
            str(index): {
                "category_pass": index < 100,
                "criteria": {"X1": {"pass": index < 100}},
            }
            for index in range(200)
        }
        stats = protocol.agreement_stats(a, copy.deepcopy(a))
        report = {**stats, **protocol.trust_result(stats)}
        receipt = {
            "run_id": "test",
            "judge_protocol_version": protocol.JUDGE_PROTOCOL_VERSION,
            "qualification_pack_sha256": protocol.qualification_pack_sha256(),
            "systems": {"ft_v2": copy.deepcopy(report), "candidate": copy.deepcopy(report)},
            "overall_trusted": True,
            "manifest_sha256": "0" * 64,
            "trust_report_sha256": "1" * 64,
            "source_bundle_sha256": {"ft_v2": "2" * 64, "candidate": "3" * 64},
            "qualification_receipt_sha256": {
                "session-a": "4" * 64,
                "session-b": "5" * 64,
            },
            "primary_output_sha256": {
                "ft_v2": {"session-a": "6" * 64, "session-b": "7" * 64},
                "candidate": {"session-a": "8" * 64, "session-b": "9" * 64},
            },
        }
        receipt["receipt_sha256"] = protocol.sha256_json(receipt)
        self.assertTrue(protocol.validate_trust_receipt(receipt, "candidate")["trusted"])
        forged = copy.deepcopy(receipt)
        forged["systems"]["candidate"]["count"] = 1
        forged["receipt_sha256"] = protocol.sha256_json({
            key: value for key, value in forged.items() if key != "receipt_sha256"
        })
        with self.assertRaisesRegex(ValueError, "exactly 200"):
            protocol.validate_trust_receipt(forged, "candidate")

    def test_one_sided_blanket_pass_with_paired_failures_is_rejected(self) -> None:
        a = {
            str(index): {"criteria": {"X1": {"pass": True}}}
            for index in range(10)
        }
        b = {
            str(index): {"criteria": {"X1": {"pass": index >= 3}}}
            for index in range(10)
        }
        with self.assertRaisesRegex(ValueError, "degenerate all-pass"):
            protocol.reject_asymmetric_constant_pass(a, b, "paired")

    def test_actual_v2_bundle_hash_is_valid(self) -> None:
        path = Path("data/checks/iteration14-judge-protocol-v2/systems/candidate/eval_report/judge_bundle.jsonl")
        row = json.loads(path.read_text().splitlines()[0])
        protocol.validate_bundle(row, "actual")
        row["answer"] += " tampered"
        with self.assertRaisesRegex(ValueError, "bundle_sha256"):
            protocol.validate_bundle(row, "actual")

    def test_build_is_blinded_and_keeps_suite_shards_private_until_unlock(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "run"
            args = SimpleNamespace(
                baseline_bundle="data/checks/iteration14-judge-protocol-v2/systems/ft_v2/eval_report/judge_bundle.jsonl",
                candidate_bundle="data/checks/iteration14-judge-protocol-v2/systems/candidate/eval_report/judge_bundle.jsonl",
                out_dir=str(out), run_id="test-paired", seed=1402, pairs_per_shard=10,
            )
            self.assertEqual(build_run(args), 0)
            manifest = json.loads((out / "run_manifest.json").read_text())
            self.assertEqual(manifest["shard_count"], 20)
            self.assertFalse((out / "shards").exists())
            plans = json.loads((out / "private/shard_plans.json").read_text())
            for plan in plans.values():
                suite = [item for item in plan["crosswalk"].values() if item["kind"] == "suite"]
                self.assertEqual(len(suite), 20)
                self.assertEqual({item["system"] for item in suite}, {"ft_v2", "candidate"})
                public = json.dumps(plan["items"])
                self.assertNotIn('"system"', public)
                positions = {item["example_id"]: index for index, item in enumerate(plan["items"])}
                by_example = {}
                for blind_id, mapping in plan["crosswalk"].items():
                    if mapping["kind"] == "suite":
                        by_example.setdefault(mapping["original_example_id"], []).append(positions[blind_id])
                self.assertTrue(all(abs(pair[0] - pair[1]) > 1 for pair in by_example.values()))

    def test_shard_lifecycle_writes_agreement_and_forbids_revalidation_or_quarantine_bypass(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "run"
            build_args = SimpleNamespace(
                baseline_bundle="data/checks/iteration14-judge-protocol-v2/systems/ft_v2/eval_report/judge_bundle.jsonl",
                candidate_bundle="data/checks/iteration14-judge-protocol-v2/systems/candidate/eval_report/judge_bundle.jsonl",
                out_dir=str(out), run_id="test-lifecycle", seed=1414, pairs_per_shard=10,
            )
            build_run(build_args)
            qualification_crosswalk = json.loads(
                (out / "private/qualification_crosswalk.json").read_text()
            )
            for session, judge in (("session-a", "judge-a"), ("session-b", "judge-b")):
                inputs = [
                    json.loads(line)
                    for line in (out / f"qualification/{session}.input.jsonl").read_text().splitlines()
                ]
                rows = [
                    golden_verdict(bundle, qualification_crosswalk[session][bundle["example_id"]], judge)
                    for bundle in inputs
                ]
                output = out / f"qualification/{session}.output.jsonl"
                write_jsonl(output, rows)
                qualify(SimpleNamespace(out_dir=str(out), session=session, verdicts=str(output)))
                unlock(SimpleNamespace(out_dir=str(out), session=session, shard=0))

            for session, judge in (("session-a", "judge-a"), ("session-b", "judge-b")):
                inputs = [
                    json.loads(line)
                    for line in (out / f"shards/00/{session}.input.jsonl").read_text().splitlines()
                ]
                crosswalk = json.loads(
                    (out / f"private/shards/00/{session}.crosswalk.json").read_text()
                )
                rows = []
                for bundle in inputs:
                    mapping = crosswalk[bundle["example_id"]]
                    if mapping["kind"] == "sentinel":
                        rows.append(golden_verdict(bundle, mapping["qualification_id"], judge))
                    else:
                        rows.append({
                            "example_id": bundle["example_id"],
                            **{key: bundle[key] for key in protocol.VERSION_KEYS},
                            "calibration_sha256": bundle["calibration_sha256"],
                            "qualification_pack_sha256": bundle["qualification_pack_sha256"],
                            "bundle_sha256": bundle["bundle_sha256"],
                            "run_id": bundle["run_id"],
                            "session_id": bundle["session_id"],
                            "shard_id": bundle["shard_id"],
                            "judge": judge,
                            "criteria": {
                                criterion_id: {"pass": True}
                                for criterion_id in bundle["expected_criteria"]
                            },
                            "category_pass": True,
                        })
                output = out / f"shards/00/{session}.output.jsonl"
                write_jsonl(output, rows)
                validate_shard(SimpleNamespace(
                    out_dir=str(out), session=session, shard=0, verdicts=str(output)
                ))

            self.assertTrue((out / "shards/00/agreement.json").exists())
            normalized = out / "validated/session-a/00.candidate.jsonl"
            original = normalized.read_text()
            normalized.write_text(original + "\n")
            with self.assertRaisesRegex(ValueError, "validated output changed"):
                write_shard_agreement_if_ready(out, "00")
            normalized.write_text(original)
            unlock(SimpleNamespace(out_dir=str(out), session="session-a", shard=1))
            with self.assertRaisesRegex(ValueError, "selective revalidation"):
                validate_shard(SimpleNamespace(
                    out_dir=str(out), session="session-a", shard=0,
                    verdicts=str(out / "shards/00/session-a.output.jsonl"),
                ))
            (out / "QUARANTINE.json").write_text(json.dumps({"failure": "test failure"}))
            with self.assertRaisesRegex(ValueError, "quarantined"):
                unlock(SimpleNamespace(out_dir=str(out), session="session-b", shard=1))


if __name__ == "__main__":
    unittest.main()
