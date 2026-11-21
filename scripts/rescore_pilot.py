#!/usr/bin/env python3
"""Score frozen outputs with the pinned reference grader and preserve originals."""

from collections import Counter
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re

from sgl_eval._vendored.nemo_skills.math_grader import extract_answer, math_equal

from pilot_common import aggregate, number


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/pilot"


def scalar_score(answer, expected, finish_reason):
    if finish_reason == "length":
        return False
    extracted = extract_answer(answer)
    if extracted is None:
        return False
    value = number(extracted)
    if value is None:
        if any(x in extracted.lower() for x in ["not ", " or ", "!=", "\\neq"]):
            return False
        matches = re.findall(r"[-−]?(?:\d[\d,]*\.?\d*|\.\d+)(?:[eE][+-]?\d+)?", extracted)
        if len(matches) != 1:
            return False
        value = number(matches[0])
    return value is not None and value == number(expected)


def main():
    raw_path = OUT / "outputs.raw.jsonl"
    remote_summary_path = OUT / "summary.remote.json"
    source = raw_path if raw_path.exists() else OUT / "outputs.jsonl"
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    assert Counter(x["passes"] for x in rows) == {1: 50, 3: 50, 6: 50}
    expected_ids = {x["id"] for x in json.loads((ROOT / "data/pilot50.json").read_text())}
    for passes in [1, 3, 6]:
        assert {x["id"] for x in rows if x["passes"] == passes} == expected_ids
    if not raw_path.exists():
        raw_path.write_bytes(source.read_bytes())
    if not remote_summary_path.exists():
        remote_summary_path.write_bytes((OUT / "summary.json").read_bytes())
    versions = {name: version(name) for name in ["sgl-eval", "math-verify", "latex2sympy2_extended", "antlr4-python3-runtime", "sympy"]}
    method = {"grader": "sgl-eval 0.1.3 vendored NeMo-Skills math_grader", "nemo_skills_revision": "645cf567ff08c0ae9cc3fc8e1edbb975b3067816", "versions": versions, "primary": "extract_answer(final_answer) then math_equal(expected, extracted); token-limit truncations fail", "secondary": "one unambiguous boxed numeric scalar, ignoring unit words and currency symbols; not the reference metric", "raw_outputs_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest()}
    for row in rows:
        row["provisional_numeric_correct"] = row["correct"]
        extracted = extract_answer(row["answer"])
        row["correct"] = row["finish_reason"] != "length" and bool(math_equal(row["expected_answer"], extracted))
        row["scalar_correct"] = scalar_score(row["answer"], row["expected_answer"], row["finish_reason"])
        row["reference_extracted_answer"] = extracted
        row["grading_method"] = method["grader"]
    (OUT / "outputs.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    summary = json.loads(remote_summary_path.read_text())
    for original in summary["summaries"]:
        selected = [row for row in rows if row["passes"] == original["passes"]]
        original.update(aggregate(selected, original["wall_seconds"]))
        original["scalar_correct"] = sum(row["scalar_correct"] for row in selected)
        original["scalar_accuracy"] = original["scalar_correct"] / len(selected)
        original["grading_method"] = method["grader"]
    summary["grading"] = method
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (OUT / "grading-provenance.json").write_text(json.dumps(method, indent=2) + "\n")
    print(json.dumps([{k: x[k] for k in ["passes", "correct", "accuracy", "scalar_correct", "scalar_accuracy"]} for x in summary["summaries"]]))


if __name__ == "__main__":
    main()
