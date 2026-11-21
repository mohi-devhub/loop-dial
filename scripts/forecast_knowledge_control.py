#!/usr/bin/env python3
"""Price an unrun knowledge control. Never creates Jobs or grader requests."""

import datetime as dt
import hashlib
import json
import math
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/publication"


def estimate(n, rate_per_minute):
    rates = {1: 1300, 3: 600, 5: 400}
    startup_seconds = 9 * 60
    avg_output_tokens = 1024
    gpu_seconds = startup_seconds + sum(n * avg_output_tokens / rate for rate in rates.values())
    gpu_nominal = math.ceil(gpu_seconds / 60) * rate_per_minute
    calls = n * 3
    judge = calls * (1200 * 2 + 64 * 8) / 1e6
    capped_seconds = startup_seconds + sum(n * 8192 / rate for rate in rates.values())
    capped_gpu = math.ceil(capped_seconds / 60) * rate_per_minute
    return {"questions": n, "passes": [1, 3, 5], "generations": calls, "gpu_nominal_seconds": gpu_seconds, "gpu_nominal_usd": gpu_nominal, "semantic_grader_nominal_usd": judge, "total_nominal_usd": gpu_nominal + judge, "all_outputs_at_8192_tokens_gpu_usd": capped_gpu, "all_outputs_capped_plus_nominal_grader_usd": capped_gpu + judge, "assumed_aggregate_tokens_per_second": rates, "assumed_mean_completion_tokens": avg_output_tokens, "server_startup_allowance_seconds": startup_seconds, "judge_assumptions": {"model": "gpt-4.1-2025-04-14", "status": "deprecated; endpoint availability and authenticated access must be checked before any paid run", "input_tokens_per_grade": 1200, "output_tokens_per_grade": 64, "input_usd_per_million": 2, "output_usd_per_million": 8, "source": "https://developers.openai.com/api/docs/models/gpt-4.1"}}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    r = requests.get("https://huggingface.co/api/jobs/hardware", timeout=20)
    r.raise_for_status()
    hardware = next(h for h in r.json() if h["name"] == "rtx-pro-6000")
    assert hardware["unitLabel"] == "minute"
    budget = json.loads((ROOT / "results/full/budget-report.json").read_text())
    assert budget["full_study_cost_upper_usd"] + 9 <= 15, "Proposed reserve exceeds the remaining study cap"
    options = [estimate(n, hardware["unitCostUSD"]) for n in [100, 200, 1000]]
    recommendation = options[1]
    result = {"status": "proposal only, not run", "new_compute_authorized": False, "new_jobs_created": 0, "checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "hardware": "HF Jobs RTX PRO 6000", "rate_usd_per_minute": hardware["unitCostUSD"], "source": "https://huggingface.co/api/jobs/hardware", "completed_study_cost_upper_usd": budget["full_study_cost_upper_usd"], "remaining_under_original_15_usd_cap": 15 - budget["full_study_cost_upper_usd"], "options": options, "recommended_questions": 200, "proposed_incremental_hard_cap_usd": 9, "combined_upper_budget_if_cap_approved_usd": budget["full_study_cost_upper_usd"] + 9, "limitations": ["Rates and output lengths are assumptions anchored to other domains; SimpleQA speed was not measured.", "The capped-output scenario is a sensitivity calculation, not a guaranteed runtime bound; a dollar watchdog must stop before the cap if performance is slower.", "Semantic grading is required. The math numeric grader is unsuitable for factual names and aliases.", "Grader API charges require separate API access and are not covered by HF credits. No grader call or credential access was attempted.", "GPT-4.1 is deprecated. Verify access and obtain agreement on a replacement or blinded manual review if it is unavailable; never silently change the grader.", "Judge cost assumes 1,200 input and 64 output tokens per final-answer grade; longer answers can increase it.", "A 200-question sample has limited power to establish small differences. A nonsignificant change would not prove knowledge equivalence."]}
    (OUT / "knowledge-control-forecast.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"questions": recommendation["questions"], "nominal_gpu_usd": recommendation["gpu_nominal_usd"], "nominal_grader_usd": recommendation["semantic_grader_nominal_usd"], "nominal_total_usd": recommendation["total_nominal_usd"], "proposed_cap_usd": 9, "new_compute_authorized": False}))


if __name__ == "__main__":
    main()
