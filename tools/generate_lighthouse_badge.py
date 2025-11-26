#!/usr/bin/env python3
"""Generate a simple SVG badge from a Lighthouse JSON report.

Usage: tools/generate_lighthouse_badge.py path/to/lighthouse-report.json path/to/output/badge.svg
"""
import json
import sys
from pathlib import Path


def score_color(score: float) -> str:
    # score is 0..1
    if score >= 0.9:
        return "#1aaf5d"  # green
    if score >= 0.75:
        return "#ffb020"  # amber
    return "#d9534f"      # red


def render_svg(label: str, value: str, color: str) -> str:
    # very small flat badge
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="160" height="20">
  <rect width="160" height="20" fill="#555" rx="3"/>
  <rect x="80" width="80" height="20" fill="{color}" rx="3"/>
  <g fill="#fff" font-family="Verdana,DejaVu Sans,Arial" font-size="11">
    <text x="10" y="14">{label}</text>
    <text x="90" y="14">{value}</text>
  </g>
</svg>'''
    return svg


def main():
    if len(sys.argv) < 3:
        print("Usage: generate_lighthouse_badge.py report.json out.svg")
        sys.exit(2)
    report = Path(sys.argv[1])
    out = Path(sys.argv[2])
    data = json.loads(report.read_text(encoding="utf-8"))
    perf = data.get("categories", {}).get("performance", {}).get("score", 0)
    access = data.get("categories", {}).get("accessibility", {}).get("score", 0)
    # format as percentages
    perf_pct = int(perf * 100)
    access_pct = int(access * 100)
    label = f"Lighthouse P/A"
    value = f"{perf_pct}% / {access_pct}%"
    # color by performance for now
    color = score_color(perf)
    out.write_text(render_svg(label, value, color), encoding="utf-8")
    print(f"Wrote badge to {out}")


if __name__ == "__main__":
    main()
