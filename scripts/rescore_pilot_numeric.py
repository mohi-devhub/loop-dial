#!/usr/bin/env python3
"""Apply the full-study math grader to the frozen pilot responses."""

import hashlib
import json
from pathlib import Path

from math_equivalence import VERSION, grade_math
from pilot_common import wilson


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/pilot"


def main():
    source = OUT / "outputs.jsonl"
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    scored = [{**row, "legacy_reference_correct": row["correct"], "legacy_grading_method": row.get("grading_method"), "grading_method": VERSION, **grade_math(row["answer"], row["expected_answer"], "gsm8k", row["finish_reason"])} for row in rows]
    summary = []
    for passes in [1, 3, 6]:
        selected = [r for r in scored if r["passes"] == passes]
        assert len(selected) == 50
        correct = sum(r.get("correct") is True for r in selected)
        summary.append({"passes": passes, "n": len(selected), "correct": correct, "raw_string_match_correct": sum(r["raw_string_match"] for r in selected), "legacy_reference_correct": sum(r["legacy_reference_correct"] for r in selected), "grader_errors": sum(bool(r.get("grader_error")) for r in selected), "wilson_95": wilson(correct, len(selected))})
    stem = "rescored-numeric-v2"
    (OUT / (stem + ".jsonl")).write_text("".join(json.dumps(r) + "\n" for r in scored))
    result = {"checkpoint_label": "thinkingmachines/TML-d24-varloop-research (varloop research checkpoint)", "grader": VERSION, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "summary": summary}
    (OUT / (stem + "-summary.json")).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
