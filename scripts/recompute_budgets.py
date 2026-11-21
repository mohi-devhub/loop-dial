"""Recompute control resource costs from saved timestamps and judge usage."""

import json
import math
from pathlib import Path

from analyze_full import read_jsonl

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / "results/knowledge"
    state = json.loads((folder / "cost-timestamps.json").read_text())
    budget = json.loads((folder / "budget-report.json").read_text())
    rows = read_jsonl(folder / "grader-output.jsonl")
    inputs = sum(r["response"]["body"]["usage"]["prompt_tokens"] for r in rows)
    outputs = sum(r["response"]["body"]["usage"]["completion_tokens"] for r in rows)
    gpu = math.ceil((state["terminal_observed_epoch"] - state["submitted_epoch"]) / 60) * state["rate_usd_per_minute"]
    judge = (inputs + outputs * 4) / 1e6
    assert gpu + judge < 5
    budget.update(gpu_timestamp_upper_usd=gpu, grader_prompt_tokens=inputs, grader_completion_tokens=outputs, grader_usage_cost_upper_usd=judge, combined_resource_cost_upper_usd=gpu + judge)
    (folder / "budget-report.json").write_text(json.dumps(budget, indent=2) + "\n")


if __name__ == "__main__":
    main()
