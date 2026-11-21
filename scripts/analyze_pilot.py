#!/usr/bin/env python3
"""Compute paired descriptive results and preserve grading caveats."""

import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/pilot"


def main():
    rows = [json.loads(x) for x in (OUT / "outputs.jsonl").read_text().splitlines()]
    groups = {p: {r["id"]: r for r in rows if r["passes"] == p} for p in [1, 3, 6]}
    ids = sorted(groups[1])
    assert len(ids) == 50 and all(set(g) == set(ids) for g in groups.values())
    rng = np.random.default_rng(271828)
    samples = rng.integers(0, len(ids), size=(10000, len(ids)))
    comparisons = []
    for lo, hi in [(1, 3), (3, 6), (1, 6)]:
        result = {"from_passes": lo, "to_passes": hi}
        for metric in ["correct", "reasoning_tokens", "completion_tokens"]:
            a = np.array([groups[lo][i][metric] for i in ids], dtype=float)
            b = np.array([groups[hi][i][metric] for i in ids], dtype=float)
            diffs = b - a
            result[metric] = {"mean_difference": float(diffs.mean()), "paired_bootstrap_95": np.percentile(diffs[samples].mean(axis=1), [2.5, 97.5]).tolist()}
            if metric != "correct":
                ratios = b[samples].mean(axis=1) / a[samples].mean(axis=1) - 1
                result[metric]["relative_mean_change"] = float(b.mean() / a.mean() - 1)
                result[metric]["relative_change_bootstrap_95"] = np.percentile(ratios, [2.5, 97.5]).tolist()
        comparisons.append(result)
    formats = []
    for row in rows:
        if not row["correct"] and row["scalar_correct"]:
            formats.append({"passes": row["passes"], "id": row["id"], "expected_answer": row["expected_answer"], "answer": row["answer"], "classification": "reference-grader formatting penalty; boxed numeric scalar correct"})
    data = {"checkpoint_label": "thinkingmachines/TML-d24-varloop-research (varloop research checkpoint)", "paired_bootstrap_seed": 271828, "paired_bootstrap_resamples": 10000, "comparisons": comparisons, "reference_format_penalties": formats, "real_scalar_errors": [r["id"] for r in rows if not r["scalar_correct"]], "truncated_outputs": sum(r["finish_reason"] == "length" for r in rows), "note": "One generation per problem per pass. Bootstrap intervals describe variation across this problem sample, not run-to-run inference noise."}
    (OUT / "paired-analysis.json").write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps({"comparisons": comparisons, "format_penalties": {p: sum(r["passes"] == p for r in formats) for p in [1, 3, 6]}}))


if __name__ == "__main__":
    main()
