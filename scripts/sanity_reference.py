#!/usr/bin/env python3
"""Recompute the secondary cookbook comparison from archived legacy grades."""

import json
from pathlib import Path
from analyze_full import read_jsonl
from pilot_common import wilson

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/full"


def main():
    records = read_jsonl(OUT / "legacy-grades.jsonl")
    assert len(records) == 300 and len({r["key"] for r in records}) == 300
    summary = []
    for passes, cookbook in [(1, 0.84), (3, 0.885)]:
        rows = [r for r in records if r["passes"] == passes and r["correct"] is not None]
        n = len(rows)
        correct = sum(r["correct"] for r in rows)
        ci = wilson(correct, n)
        summary.append({"passes": passes, "scored": n, "correct": correct, "accuracy": correct / n, "wilson_95": ci, "cookbook_reference": cookbook, "reference_inside_ci": ci[0] <= cookbook <= ci[1]})
    result = {"checkpoint_label": "thinkingmachines/TML-d24-varloop-research (varloop research checkpoint)", "metric": "sgl-eval 0.1.3 vendored NeMo-Skills math_grader (secondary sanity check only)", "summary": summary}
    (OUT / "gsm8k-legacy-sanity.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
