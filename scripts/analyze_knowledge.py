#!/usr/bin/env python3
"""Analyze the completed paired SimpleQA control without further inference."""

from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np

from analyze_full import BOOTSTRAPS, SEED, describe, indices, paired, read_jsonl


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/knowledge"


def main():
    config = json.loads((ROOT / "knowledge-config.json").read_text())
    rows = read_jsonl(OUT / "scored-outputs.jsonl")
    assert len(rows) == 600 and not any(r.get("error") for r in rows)
    tasks = json.loads((ROOT / "data/knowledge/simpleqa200.json").read_text())
    task_ids = {r["id"] for r in tasks}
    groups = {p: {r["id"]: r for r in rows if r["passes"] == p} for p in [1, 3, 5]}
    assert all(set(g) == task_ids for g in groups.values())
    events = {e["passes"]: e for e in read_jsonl(OUT / "events.jsonl") if e["kind"] == "batch" and not e["phase"].startswith("warmup-")}
    summaries = []
    for passes, group in groups.items():
        selected = [group[i] for i in sorted(group)]
        for row in selected:
            row["api_reasoning_tokens"] = row["usage"].get("reasoning_tokens")
        sampled = indices(selected, np.random.default_rng(SEED))
        tokens = np.array([r["reasoning_tokens"] for r in selected], dtype=float)
        summaries.append({"passes": passes, **describe(selected, events[passes], 200), "reasoning_mean_95": np.percentile(tokens[sampled].mean(axis=1), [2.5, 97.5]).tolist(), "grade_counts": dict(Counter(r["grade_str"] for r in selected))})
    comparisons = [{"from_passes": lo, "to_passes": hi, "status": "requested primary comparison" if (lo, hi) == (1, 3) else "exploratory", **paired(groups[lo], groups[hi])} for lo, hi in [(1, 3), (3, 5), (1, 5)]]
    source_files = [OUT / "scored-outputs.jsonl.gz", ROOT / "knowledge-config.json", ROOT / "data/knowledge/manifest.json"]
    result = {"checkpoint_label": config["checkpoint_label"], "model": config["model"], "revision": config["revision"], "dataset": "google/simpleqa-verified", "dataset_revision": config["dataset_revision"], "distinct_questions": 200, "scored_outputs": len(rows), "conditions": summaries, "paired_comparisons": comparisons, "official_grader": config["official_grader"], "grading_input": "Final answer channel only", "accuracy_definition": "CORRECT / 200, including INCORRECT and NOT_ATTEMPTED in denominator", "token_definition": "visible reasoning retokenized using checkpoint tokenizer; API counts retained separately", "bootstrap_draws": BOOTSTRAPS, "bootstrap_seed": SEED, "interpretation_limit": "Non-significance is not evidence of equivalence or proof that knowledge stays flat; no equivalence margin was specified.", "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}, "new_inference_from_analysis": False}
    (OUT / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"scored_outputs": len(rows), "accuracy_by_pass": {r["passes"]: r["accuracy"] for r in summaries}, "one_vs_three_mcnemar": comparisons[0]["mcnemar"]}))


if __name__ == "__main__":
    main()
