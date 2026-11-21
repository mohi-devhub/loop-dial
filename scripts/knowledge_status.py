#!/usr/bin/env python3
"""Read local collection state without starting compute or exposing credentials."""

from collections import Counter
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/knowledge"


def main():
    state = json.loads((OUT / "job-state.json").read_text())
    records = []
    path = OUT / "outputs.jsonl"
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    result = {"job_id": state["job_id"], "gpu_stage": state["stage"], "elapsed_minutes_upper": round((state["last_observed_epoch"] - state["submitted_epoch"]) / 60, 2), "gpu_cost_upper_usd": state["conservative_cost_upper_usd"], "outputs_by_pass": dict(Counter(r["passes"] for r in records)), "inference_errors": sum(bool(r.get("error")) for r in records), "truncations": sum(r.get("finish_reason") == "length" for r in records), "cap_usd": 5}
    if (OUT / "grader-batch-state.json").exists():
        batch = json.loads((OUT / "grader-batch-state.json").read_text())
        result["official_grading"] = {"id": batch["id"], "status": batch["status"], "counts": batch.get("request_counts")}
    if (OUT / "budget-report.json").exists():
        result["combined_resource_cost_upper_usd"] = json.loads((OUT / "budget-report.json").read_text())["combined_resource_cost_upper_usd"]
    print(json.dumps(result))


if __name__ == "__main__":
    main()
