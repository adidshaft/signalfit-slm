#!/usr/bin/env bash
# Ship-verification: fuse a promoted LoRA adapter, 4-bit quantize it, and
# RE-RUN the full 200-case prefilter on the QUANTIZED model. Quantization can
# shift behavior, so a promoted fp16 model is not shippable until the quantized
# build clears the same gates and protect sets. This is the last gate before
# an on-device release.
#
# Usage:
#   scripts/ship_verify.sh <adapter_dir> <tag>
# Example:
#   scripts/ship_verify.sh models/adapters/ft_v10_qwen3-1.7b ft_v10
#
# Produces under data/checks/ship-<tag>/:
#   fused/            fp16 fused model
#   export-4bit/      quantized on-device model (the shippable artifact)
#   suite_generations.jsonl, eval_report/, prefilter.json, SHIP_VERDICT.md
set -euo pipefail

ADAPTER="${1:?adapter dir required}"
TAG="${2:?tag required}"
BASE="Qwen/Qwen3-1.7B"
PY=.venv/bin/python
OUT="data/checks/ship-${TAG}"
FUSED="${OUT}/fused"
EXPORT="${OUT}/export-4bit"
mkdir -p "${OUT}"

echo "== 1/5 fuse adapter -> fp16 standalone"
.venv/bin/mlx_lm.fuse --model "${BASE}" --adapter-path "${ADAPTER}" --save-path "${FUSED}"

echo "== 2/5 quantize fused -> 4-bit (the shippable artifact)"
.venv/bin/mlx_lm.convert --hf-path "${FUSED}" -q --q-bits 4 --q-group-size 64 --mlx-path "${EXPORT}"

echo "== 3/5 run the 200-case suite through wrapper v7 on the QUANTIZED model"
# Note: the quantized model is a full standalone model, so --model points at it
# and no --adapter is passed.
PYTHONUNBUFFERED=1 ${PY} scripts/answer_with_check.py \
  --examples eval/v1/cases --model "${EXPORT}" \
  -o "${OUT}/suite_generations.jsonl" \
  --correction-log "${OUT}/correction_log.jsonl"

echo "== 4/5 score under sf-gates-12"
${PY} scripts/run_eval.py --examples eval/v1/cases \
  --generations "${OUT}/suite_generations.jsonl" --out-dir "${OUT}/eval_report" > /dev/null

echo "== 5/5 prefilter the QUANTIZED model against protects"
${PY} scripts/check_sweep_candidate.py \
  --baseline eval/v1/baseline/ft_v2.judged_report.json \
  --candidate "${OUT}/eval_report/eval_report.json" \
  --additional-protect-report data/checks/iteration17a-sf-gates-12/prior-gain.judged_report.json \
  > "${OUT}/prefilter.json"

${PY} - "$OUT" "$TAG" <<'PYEOF'
import json, sys
out, tag = sys.argv[1], sys.argv[2]
pf = json.load(open(f"{out}/prefilter.json"))
rep = json.load(open(f"{out}/eval_report/eval_report.json"))["summary"]
survivor = pf["survivor"]
verdict = "SHIP_OK" if survivor else "SHIP_BLOCKED"
lines = [
    f"# Ship verification — {tag} (quantized 4-bit)", "",
    f"**Verdict: {verdict}**", "",
    f"- deterministic: {rep['deterministic_pass_rate']}",
    f"- survivor (clears all protects): {survivor}",
    f"- protect_failures: {pf['protect_failures']}",
    f"- secondary_protect_failures: {pf['secondary_protect_failures']}", "",
    "The shippable artifact is `export-4bit/`. It is releasable only when this",
    "verdict is SHIP_OK — i.e. the QUANTIZED model clears the same gates and",
    "protect sets the fp16 model did. If SHIP_BLOCKED, quantization degraded",
    "behavior and the model must not ship as-is.",
]
open(f"{out}/SHIP_VERDICT.md", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
PYEOF
