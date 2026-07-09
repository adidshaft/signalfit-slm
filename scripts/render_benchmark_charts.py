#!/usr/bin/env python3
"""Render README benchmark charts from pinned judged reports using stdlib only."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets"
REPORTS = {
    "ft_v2": ROOT / "eval/v1/baseline/ft_v2.judged_report.json",
    "ft_v4": ROOT / "data/ft_v4/eval_suite_v1/eval_report/judged_report.json",
    "ft_v5": ROOT / "data/ft_v5/eval_suite_v1/eval_report/judged_report.json",
}
COLORS = {"ft_v2": "#334155", "ft_v4": "#0f766e", "ft_v5": "#b45309"}


def load_reports() -> dict[str, dict]:
    reports = {name: json.loads(path.read_text()) for name, path in REPORTS.items()}
    triples = {
        (report["summary"]["gate_version"], report["summary"]["rubric_version"])
        for report in reports.values()
    }
    if triples != {("sf-gates-6", "rubric-v0.1")}:
        raise SystemExit(f"benchmark reports are not comparable: {sorted(triples)}")
    if {report["summary"]["count"] for report in reports.values()} != {66}:
        raise SystemExit("benchmark reports do not all cover 66 cases")
    return reports


def text(x: float, y: float, value: str, *, size: int = 18, anchor: str = "start",
         weight: int = 400, fill: str = "#172033") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="Inter,Arial,sans-serif" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}">{value}</text>'
    )


def svg_document(width: int, height: int, body: list[str], title: str) -> str:
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{title}</title>',
        '<desc id="desc">SignalFit-SLM benchmark comparison generated from judged reports.</desc>',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        *body,
        '</svg>',
        '',
    ])


def render_overall(reports: dict[str, dict]) -> None:
    width, height = 1200, 650
    left, right, top, bottom = 105, 55, 145, 105
    chart_w, chart_h = width - left - right, height - top - bottom
    metrics = [
        ("Deterministic", "deterministic_pass_rate"),
        ("Judge category", "judge_category_pass_rate"),
        ("Strict overall", "overall_pass_rate"),
    ]
    body = [
        text(left, 52, "Frozen-suite benchmark", size=30, weight=500),
        text(left, 83, "Passed cases out of 66 | sf-eval-v1, sf-gates-6, rubric-v0.1", size=17, fill="#526176"),
    ]
    for idx, name in enumerate(REPORTS):
        lx = 690 + idx * 155
        body.append(f'<rect x="{lx}" y="37" width="18" height="18" rx="2" fill="{COLORS[name]}"/>')
        body.append(text(lx + 27, 52, name, size=17))
    for tick in range(0, 67, 11):
        y = top + chart_h - (tick / 66) * chart_h
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#dce2ea"/>')
        body.append(text(left - 16, y + 6, str(tick), size=15, anchor="end", fill="#64748b"))
    group_w = chart_w / len(metrics)
    bar_w, gap = 58, 14
    run_count = len(REPORTS)
    for mi, (label, key) in enumerate(metrics):
        center = left + group_w * (mi + 0.5)
        start = center - (run_count * bar_w + (run_count - 1) * gap) / 2
        for ri, name in enumerate(REPORTS):
            summary = reports[name]["summary"]
            count = round(summary[key] * summary["count"])
            bar_h = count / 66 * chart_h
            x, y = start + ri * (bar_w + gap), top + chart_h - bar_h
            body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w}" height="{bar_h:.1f}" rx="4" fill="{COLORS[name]}"/>')
            body.append(text(x + bar_w / 2, y - 10, f"{count}/66", size=16, anchor="middle", weight=500))
        body.append(text(center, top + chart_h + 42, label, size=18, anchor="middle", weight=500))
    body.append(text(width / 2, height - 25, "Higher aggregate scores do not override a safety-gate regression.", size=17, anchor="middle", fill="#526176"))
    (OUT / "benchmark-overall.svg").write_text(svg_document(width, height, body, "SignalFit-SLM overall benchmark"))


def render_gates(reports: dict[str, dict]) -> None:
    width, height = 1200, 820
    left, right, top, bottom = 285, 135, 165, 50
    chart_w = width - left - right
    gates = [
        ("x1 Grounding", "x1_grounding"),
        ("x4 Follow-up budget", "x4_followups"),
        ("x5 No brands", "x5_brands"),
        ("x6 Response length", "x6_length"),
        ("s1 Triage safety", "s1_no_coaching_in_triage"),
        ("s2 Refusal safety", "s2_no_protocol_in_refusal"),
        ("s3 Field binding", "s3_field_binding"),
        ("s4 Comparative arithmetic", "s4_comparative_arithmetic"),
        ("s5 Claim discipline", "s5_claim_discipline"),
    ]
    lo, hi = 70.0, 100.0

    def xpos(rate: float) -> float:
        return left + ((rate - lo) / (hi - lo)) * chart_w

    body = [
        text(80, 52, "Safety and grounding gates", size=30, weight=500),
        text(80, 83, "ft_v2 model of record vs blocked ft_v4 and ft_v5 candidates | pass rate", size=17, fill="#526176"),
    ]
    for idx, name in enumerate(REPORTS):
        lx = 735 + idx * 120
        body.append(f'<circle cx="{lx}" cy="49" r="8" fill="{COLORS[name]}"/>')
        body.append(text(lx + 17, 55, name, size=17))
    for tick in (70, 80, 90, 100):
        x = xpos(tick)
        body.append(f'<line x1="{x:.1f}" y1="{top-20}" x2="{x:.1f}" y2="{height-bottom}" stroke="#dce2ea"/>')
        body.append(text(x, top - 34, f"{tick}%", size=15, anchor="middle", fill="#64748b"))
    row_h = (height - top - bottom) / len(gates)
    for idx, (label, key) in enumerate(gates):
        y = top + row_h * (idx + 0.5)
        body.append(text(left - 24, y + 6, label, size=17, anchor="end", weight=500 if key.startswith("s1_") else 400))
        for ri, name in enumerate(REPORTS):
            gate = reports[name]["summary"]["by_gate"][key]
            rate = 100 * gate["pass"] / gate["n"]
            px, py = xpos(rate), y + (ri - 1) * 15
            body.append(f'<line x1="{left}" y1="{py:.1f}" x2="{px:.1f}" y2="{py:.1f}" stroke="{COLORS[name]}" stroke-width="3" stroke-linecap="round" opacity="0.55"/>')
            body.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="7" fill="{COLORS[name]}" stroke="#ffffff" stroke-width="2"/>')
            body.append(text(px + 12, py + 5, f'{gate["pass"]}/{gate["n"]}', size=13, fill=COLORS[name]))
        if key == "s1_no_coaching_in_triage":
            body.append(text(width - right + 18, y + 6, "BLOCK v4/v5", size=14, weight=500, fill="#dc2626"))
    (OUT / "benchmark-gates.svg").write_text(svg_document(width, height, body, "SignalFit-SLM gate comparison"))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    reports = load_reports()
    render_overall(reports)
    render_gates(reports)
    print("rendered docs/assets/benchmark-overall.svg")
    print("rendered docs/assets/benchmark-gates.svg")


if __name__ == "__main__":
    main()
