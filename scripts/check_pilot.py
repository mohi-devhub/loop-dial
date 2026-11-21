"""Recompute the pilot's reported counts and Wilson intervals from saved grades."""

import json
from pathlib import Path

from analyze_full import read_jsonl
from pilot_common import wilson

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / "results/pilot"
    rows = read_jsonl(folder / "rescored-numeric-v2.jsonl")
    assert len(rows) == 150
    summaries = []
    for passes in [1, 3, 6]:
        selected = [r for r in rows if r["passes"] == passes]
        correct = sum(r["correct"] for r in selected)
        summaries.append({"passes": passes, "n": len(selected), "correct": correct, "raw_string_match_correct": sum(r["raw_string_match"] for r in selected), "legacy_reference_correct": sum(r["legacy_reference_correct"] for r in selected), "grader_errors": sum(bool(r.get("grader_error")) for r in selected), "wilson_95": wilson(correct, len(selected))})
    target = folder / "rescored-numeric-v2-summary.json"
    prior = json.loads(target.read_text())
    prior["summary"] = summaries
    target.write_text(json.dumps(prior, indent=2) + "\n")


if __name__ == "__main__":
    main()
