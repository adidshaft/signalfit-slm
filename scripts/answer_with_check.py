#!/usr/bin/env python3
"""Generate SignalFit answers with one bounded answer-side correction retry.

The wrapper is intentionally a system-level layer, rather than a change to the
frozen evaluator.  It imports ``check`` from :mod:`run_eval` and considers only
the four answer-side checks that can be corrected from the draft itself:
``x1_grounding``, ``x4_followups``, a serving-safe ``x6_length`` proxy,
``s3_field_binding``, ``s4_comparative_arithmetic``, and
``s5_claim_discipline``.  A failed draft gets exactly one retry, with its
specific gate errors included in the retry turn.  The retry is final even if it
still fails; the correction log records that outcome for honest system scoring.

The serving wrapper intentionally does not use an evaluator-only expected
action.  Its length proxy retries every draft over 190 words, and applies the
tighter 80-word ceiling only when the draft starts by declining a request.  It
therefore avoids guessing a short target for ordinary coaching answers while
still correcting the refusal shape that is observable at inference time.

Examples mode produces the usual ``{example_id, answer}`` JSONL accepted by
``run_eval.py``.  For a serving-style one-off, pass a complete eval example to
``--context``, or a context object plus ``--expected-action``.  ``--drafts``
and ``--retries`` accept JSONL answers and avoid loading MLX, so the retry path
can be tested or replayed deterministically.

Example:
    .venv/bin/python scripts/answer_with_check.py \\
      --examples eval/v1/cases --model Qwen/Qwen3-1.7B \\
      --adapter models/adapters/ft_v6_qwen3-1.7b \\
      --chat-template-config '{"enable_thinking":false}' \\
      -o data/ft_v6_qwen3_1.7b_verify_retry/suite_generations.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Callable, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_dataset import SYSTEM_PROMPT, model_input_context  # noqa: E402
from run_eval import check  # noqa: E402 -- deliberately reuse frozen gate logic


ANSWER_SIDE_GATES = (
    "x1_grounding",
    "x4_followups",
    "x6_length",
    "s3_field_binding",
    "s4_comparative_arithmetic",
    "s5_claim_discipline",
)

# A deliberately narrow observable proxy for a refusal-shaped draft.  Do not
# infer this from the eval expected_action: serving contexts do not have it.
REFUSAL_OPENERS = (
    "i can't",
    "i can’t",
    "i cannot",
    "i'm not able",
    "i’m not able",
    "i am not able",
    "i'm unable",
    "i’m unable",
    "i am unable",
    "i won't",
    "i won’t",
    "i will not",
)


def serving_length_check(answer: str) -> dict:
    """Check only length constraints observable without expected_action.

    The frozen evaluator remains the scorer.  This wrapper proxy is a
    conservative retry policy: any response above the largest evaluator upper
    bound is corrected, and a decline-led response gets the refusal ceiling.
    """
    words = len(answer.split())
    normalized = answer.lstrip(" \t\n\"'“”‘’([{<").casefold()
    refusal_shaped = normalized.startswith(REFUSAL_OPENERS)
    bound = 80 if refusal_shaped else 190
    return {
        "pass": words <= bound,
        "words": words,
        "bounds": [0, bound],
        "policy": "refusal_shaped" if refusal_shaped else "all_actions",
    }


def answer_side_checks(example: dict, answer: str) -> dict:
    """Run exactly the reusable answer-side checks needed by this wrapper."""
    all_checks = check(example, answer)
    selected = {name: all_checks[name] for name in ANSWER_SIDE_GATES if name != "x6_length"}
    selected["x6_length"] = serving_length_check(answer)
    return selected


def failed_checks(checks: dict) -> dict:
    """Return only failed answer-side gates, preserving evaluator detail."""
    return {name: result for name, result in checks.items() if not result["pass"]}


def correction_errors(failures: dict) -> list[str]:
    """Render evaluator output into concrete, model-readable retry feedback."""
    errors = []
    for gate, result in failures.items():
        if gate == "x1_grounding":
            values = result["ungrounded"]
            errors.append(f"{gate}: ungrounded number-and-unit values: {values}")
        elif gate == "x4_followups":
            errors.append(f"{gate}: use at most one follow-up question (found {result['questions']})")
        elif gate == "x6_length":
            errors.append(
                f"{gate}: response is {result['words']} words; keep it at or below "
                f"{result['bounds'][1]} words ({result['policy']} serving policy)"
            )
        else:
            errors.extend(f"{gate}: {error}" for error in result["errors"])
    return errors


def base_messages(example: dict) -> list[dict[str, str]]:
    context = json.dumps(
        model_input_context(example["context"]),
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
    )
    question = example["context"]["request"]["user_question"]
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {question}"},
    ]


def retry_messages(example: dict, draft: str, errors: list[str]) -> list[dict[str, str]]:
    """Append a correction turn without changing the original task context."""
    feedback = "\n".join(f"- {error}" for error in errors)
    return base_messages(example) + [
        {"role": "assistant", "content": draft},
        {
            "role": "user",
            "content": (
                "The previous draft did not pass deterministic answer checks. "
                "Return only a corrected final answer. Fix the listed issues while "
                "remaining responsive to the original question and following the "
                "system safety instructions. Do not mention these checks.\n\n"
                f"CHECK FAILURES:\n{feedback}"
            ),
        },
    ]


def run_one(
    example: dict,
    generate: Callable[[list[dict[str, str]]], tuple[str, float | None, str]],
) -> tuple[dict, dict]:
    """Generate one answer and, only when required, its one corrective retry."""
    draft, draft_latency_ms, draft_source = generate(base_messages(example))
    draft = draft.strip()
    draft_checks = answer_side_checks(example, draft)
    failures = failed_checks(draft_checks)

    retry_triggered = bool(failures)
    retry_latency_ms = None
    retry_source = None
    retry_checks = None
    final_answer = draft
    final_checks = draft_checks
    errors = correction_errors(failures)
    if retry_triggered:
        final_answer, retry_latency_ms, retry_source = generate(
            retry_messages(example, draft, errors)
        )
        final_answer = final_answer.strip()
        retry_checks = answer_side_checks(example, final_answer)
        final_checks = retry_checks

    generation = {"example_id": example["example_id"], "answer": final_answer}
    log = {
        "example_id": example["example_id"],
        "retry_triggered": retry_triggered,
        "draft_source": draft_source,
        "retry_source": retry_source,
        "draft_latency_ms": draft_latency_ms,
        "retry_latency_ms": retry_latency_ms,
        "draft_checks": draft_checks,
        "failures": failures,
        "correction_errors": errors,
        "retry_checks": retry_checks,
        "final_checks": final_checks,
        "final_answer_source": "retry" if retry_triggered else "draft",
        "final_answer_side_pass": not bool(failed_checks(final_checks)),
    }
    return generation, log


def jsonl_answers(path: Path) -> dict[str, str]:
    answers = {}
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row.get("example_id"), str) or not isinstance(row.get("answer"), str):
            raise ValueError(f"{path}:{line_no} needs string example_id and answer fields")
        if row["example_id"] in answers:
            raise ValueError(f"duplicate example_id {row['example_id']!r} in {path}")
        answers[row["example_id"]] = row["answer"]
    return answers


def examples_from_paths(paths: Iterable[str]) -> list[dict]:
    examples = []
    seen = set()
    for raw_path in paths:
        path = Path(raw_path)
        files = [path] if path.is_file() else sorted(path.rglob("*.json"))
        if not files:
            raise ValueError(f"no JSON examples found at {path}")
        for file_path in files:
            example = json.loads(file_path.read_text())
            example_id = example.get("example_id")
            if not isinstance(example_id, str):
                raise ValueError(f"{file_path} is not an eval example (missing example_id)")
            if example_id in seen:
                raise ValueError(f"duplicate example_id {example_id!r} in inputs")
            seen.add(example_id)
            examples.append(example)
    return examples


def single_context_example(raw: dict, expected_action: str | None, example_id: str) -> dict:
    """Accept either a complete eval example or a serving context object."""
    if "context" in raw and "target_response" in raw:
        return raw
    if expected_action is None:
        raise ValueError("--expected-action is required when --context is a context object")
    if "request" not in raw:
        raise ValueError("--context must be a complete eval example or a context with request")
    return {
        "example_id": example_id,
        "context": raw,
        "task_category": raw.get("task", {}).get("category", "serving"),
        "target_response": {"expected_action": expected_action},
    }


class LazyMLXGenerator:
    """Load MLX only if an injected answer is unavailable for a generation."""

    def __init__(self, model_name: str, adapter: str | None, max_tokens: int, config: dict):
        self.model_name = model_name
        self.adapter = adapter
        self.max_tokens = max_tokens
        self.config = config
        self.model = None
        self.tokenizer = None

    def __call__(self, messages: list[dict[str, str]]) -> tuple[str, float, str]:
        if self.model is None:
            try:
                from mlx_lm import generate, load
            except ImportError as exc:
                raise SystemExit("mlx-lm not installed: .venv/bin/pip install mlx-lm") from exc
            self.model, self.tokenizer = load(self.model_name, adapter_path=self.adapter)
            self._generate = generate
        prompt = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, **self.config
        )
        started = time.perf_counter()
        answer = self._generate(self.model, self.tokenizer, prompt=prompt, max_tokens=self.max_tokens)
        return answer, round((time.perf_counter() - started) * 1000, 1), "mlx"


def default_log_path(out_path: Path) -> Path:
    suffix = out_path.suffix or ".jsonl"
    return out_path.with_name(f"{out_path.stem}.correction_log{suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--examples", nargs="+", help="eval example directory/directories or JSON files")
    inputs.add_argument("--context", type=Path, help="one complete eval example or serving context JSON")
    parser.add_argument("--expected-action", choices=("answer", "answer_with_caveat", "followup", "triage", "refuse"))
    parser.add_argument("--example-id", default="single-context", help="id used for a bare --context object")
    parser.add_argument("--model", default="Qwen/Qwen3-1.7B")
    parser.add_argument("--adapter", default=None)
    parser.add_argument("--max-tokens", type=int, default=350)
    parser.add_argument("--chat-template-config", default='{"enable_thinking":false}')
    parser.add_argument("--drafts", type=Path, help="injected draft answer JSONL (test/replay mode)")
    parser.add_argument("--retries", type=Path, help="injected retry answer JSONL (test/replay mode)")
    parser.add_argument("-o", "--out", type=Path, required=True, help="final {example_id,answer} JSONL")
    parser.add_argument("--correction-log", type=Path, help="per-answer correction log JSONL")
    args = parser.parse_args()

    try:
        chat_template_config = json.loads(args.chat_template_config)
    except json.JSONDecodeError as exc:
        parser.error(f"invalid --chat-template-config JSON: {exc.msg}")
    if not isinstance(chat_template_config, dict):
        parser.error("--chat-template-config must decode to a JSON object")

    try:
        examples = (
            examples_from_paths(args.examples)
            if args.examples
            else [single_context_example(json.loads(args.context.read_text()), args.expected_action, args.example_id)]
        )
        injected_drafts = jsonl_answers(args.drafts) if args.drafts else {}
        injected_retries = jsonl_answers(args.retries) if args.retries else {}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    mlx_generate = LazyMLXGenerator(args.model, args.adapter, args.max_tokens, chat_template_config)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    log_path = args.correction_log or default_log_path(args.out)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    retry_count = 0
    with args.out.open("w") as out_file, log_path.open("w") as log_file:
        for example in examples:
            example_id = example["example_id"]
            attempts = 0

            def generate(messages: list[dict[str, str]]) -> tuple[str, float | None, str]:
                nonlocal attempts
                attempts += 1
                injected = injected_drafts if attempts == 1 else injected_retries
                if example_id in injected:
                    return injected[example_id], None, "injected"
                return mlx_generate(messages)

            generation, log = run_one(example, generate)
            retry_count += int(log["retry_triggered"])
            out_file.write(json.dumps(generation, ensure_ascii=False) + "\n")
            log_file.write(json.dumps(log, ensure_ascii=False) + "\n")
            print(
                f"generated {example_id} ({len(generation['answer'].split())} words; "
                f"retry={'yes' if log['retry_triggered'] else 'no'})"
            )
    print(f"-> {args.out}")
    print(f"correction log -> {log_path}")
    print(f"retry rate: {retry_count}/{len(examples)} ({retry_count / len(examples):.1%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
