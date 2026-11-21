#!/usr/bin/env python3
"""Report observed pilot data and cost scenarios without inventing measurements."""

import json
from pathlib import Path

from pilot_common import LABEL


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/pilot"
RATE = 2.75
BASE_LENGTHS = {"GSM8K": 1024, "MATH-500": 3072, "HumanEval": 1024, "GPQA": 3072}


def interpolate(known, passes):
    if passes in known:
        return known[passes]
    lo = max(p for p in known if p < passes)
    hi = min(p for p in known if p > passes)
    return known[lo] + (known[hi] - known[lo]) * (passes - lo) / (hi - lo)


def estimate(case, timing, length_ratio, overhead_hours, baseline_lengths):
    seconds = 0
    generations = 0
    weighted_tokens = 0
    for passes in range(1, 7):
        for domain, count in case["domains"].items():
            if passes == 6 and case.get("pass6_math_only") and domain not in ["GSM8K", "MATH-500"]:
                continue
            tokens = count * baseline_lengths[domain] * length_ratio[passes]
            seconds += tokens * timing[passes]
            weighted_tokens += tokens * (passes + 1) / 4
            generations += count
    for passes in case["shared_passes"]:
        for domain, count in case["domains"].items():
            tokens = count * baseline_lengths[domain] * length_ratio[passes]
            seconds += tokens * timing[passes]
            weighted_tokens += tokens * (passes + 1) / 4
            generations += count
    for passes in [1, 3]:
        for domain in case["repeat_domains"]:
            count = case["domains"][domain] * 3
            tokens = count * baseline_lengths[domain] * length_ratio[passes]
            seconds += tokens * timing[passes]
            weighted_tokens += tokens * (passes + 1) / 4
            generations += count
    control_passes = 6 if case["name"] == "Original study" else 5
    control_cap = 2340 if control_passes == 6 else 2730
    control_count = 25 * len(case["domains"])
    control_tokens = control_count * control_cap
    seconds += control_tokens * timing[control_passes]
    weighted_tokens += control_tokens * (control_passes + 1) / 4
    generations += control_count
    gpu_hours = seconds / 3600 + overhead_hours
    stressed_hours = seconds * 1.25 / 3600 + overhead_hours
    return {"name": case["name"], "case": case, "generations": generations, "compute_control": {"passes": control_passes, "max_tokens": control_cap, "count": control_count}, "three_pass_equivalent_tokens": weighted_tokens, "gpu_hours": gpu_hours, "gpu_usd": gpu_hours * RATE, "cpu_reserve_usd": 0.75, "contingency_usd": 1.75, "total_usd": gpu_hours * RATE + 2.50, "total_with_25_percent_longer_decode_usd": stressed_hours * RATE + 2.50}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summary_path = OUT / "summary.json"
    observed = json.loads(summary_path.read_text()) if summary_path.exists() else None
    preflight_path = OUT / "preflight.json"
    preflight = json.loads(preflight_path.read_text()) if preflight_path.exists() else {}
    state_path = OUT / "job-state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else None
    complete = observed is not None and len(observed["summaries"]) == 3 and all(x["attempted"] == 50 and x["errors"] == 0 for x in observed["summaries"])
    method = "observed GSM8K pilot rates; interpolated unmeasured pass counts and assumed other-domain lengths" if complete else "Phase 0 assumptions only; no pilot measurements"
    if complete:
        per_pass = {x["passes"]: x for x in observed["summaries"]}
        known_times = {p: 1 / x["aggregate_tokens_per_second"] for p, x in per_pass.items()}
        known_lengths = {p: x["mean_completion_tokens"] / per_pass[3]["mean_completion_tokens"] for p, x in per_pass.items()}
        timing = {p: interpolate(known_times, p) for p in range(1, 7)}
        length_ratio = {p: interpolate(known_lengths, p) for p in range(1, 7)}
        baseline_lengths = {**BASE_LENGTHS, "GSM8K": per_pass[3]["mean_completion_tokens"]}
        events = [json.loads(line) for line in (OUT / "events.jsonl").read_text().splitlines()]
        ready = [x for x in events if x["kind"] == "server_ready"]
        first_load = ready[0]["worker_elapsed_seconds"]
        switching = sum(x["startup_seconds"] for x in ready[1:]) / max(1, len(ready) - 1)
        overhead_hours = (first_load + 13 * switching + 120) / 3600
    else:
        timing = {p: (p + 1) / 4 / 500 for p in range(1, 7)}
        length_ratio = {p: 1 for p in range(1, 7)}
        baseline_lengths = dict(BASE_LENGTHS)
        overhead_hours = 0.75
    cases = [
        {"name": "Original study", "domains": {"GSM8K": 300, "MATH-500": 200, "HumanEval": 164, "GPQA": 100}, "repeat_domains": ["GSM8K", "MATH-500", "HumanEval", "GPQA"], "shared_passes": [3, 6]},
        {"name": "Requested trims, GPQA 60", "domains": {"GSM8K": 300, "MATH-500": 200, "HumanEval": 164, "GPQA": 60}, "repeat_domains": ["GSM8K", "HumanEval"], "shared_passes": [3, 5], "pass6_math_only": True},
        {"name": "Requested trims, drop GPQA", "domains": {"GSM8K": 300, "MATH-500": 200, "HumanEval": 164}, "repeat_domains": ["GSM8K", "HumanEval"], "shared_passes": [3, 5], "pass6_math_only": True},
        {"name": "Smaller math subsets, drop GPQA", "domains": {"GSM8K": 200, "MATH-500": 100, "HumanEval": 164}, "repeat_domains": ["GSM8K", "HumanEval"], "shared_passes": [3, 5], "pass6_math_only": True},
        {"name": "Smaller math subsets, GPQA 60", "domains": {"GSM8K": 200, "MATH-500": 100, "HumanEval": 164, "GPQA": 60}, "repeat_domains": ["GSM8K", "HumanEval"], "shared_passes": [3, 5], "pass6_math_only": True},
    ]
    projections = [estimate(case, timing, length_ratio, overhead_hours, baseline_lengths) for case in cases]
    pilot_cost_upper = state.get("conservative_cost_upper_usd") if state else 0
    allowed_full_budget = min(18, 20 - (pilot_cost_upper if state else 3))
    status = "complete" if complete else "not_run_authentication_missing" if not preflight.get("authenticated") and not state else "incomplete"
    readings_path = OUT / "user-cost-readings.json"
    readings = json.loads(readings_path.read_text()) if readings_path.exists() else []
    final_balance = next((x["remaining_credit_usd"] for x in reversed(readings) if x["reading_type"] == "final_after_pilot"), None)
    opening = next((x["remaining_credit_usd"] for x in readings if x["reading_type"] == "approximate_opening"), None)
    cost_approx = round(opening - final_balance, 2) if opening is not None and final_balance is not None else None
    cost_method = f"User reports final credit ${final_balance:.2f} against approximately ${opening:.2f} before the pilot. About ${cost_approx:.2f} spent; exact opening balance and invoice unavailable. Independent bound uses submission-to-terminal time for both jobs, rounded up by minute." if cost_approx is not None else "Provider invoice not retrieved. Job submission-to-terminal time upper-bounds billable duration, rounded up by minute." if state else "No job created; actual spend is zero."
    analysis = {"checkpoint_label": LABEL, "status": status, "pilot_complete": complete, "actual_pilot_invoice_usd": None, "pilot_cost_approx_usd": cost_approx, "user_reported_final_credit_usd": final_balance, "pilot_cost_conservative_upper_usd": pilot_cost_upper, "cost_method": cost_method, "projection_method": method, "projected_overhead_hours": overhead_hours, "full_budget_limit_usd": allowed_full_budget, "full_run_authorized": False, "projections": projections}
    (OUT / "analysis.json").write_text(json.dumps(analysis, indent=2) + "\n")
    lines = ["# Loop Dial pilot report", "", f"Checkpoint: **{LABEL}**. Model ID: `thinkingmachines/TML-d24-varloop-research`.", ""]
    if not complete:
        lines += ["**Pilot measurements are unavailable.**" if not state else "**The pilot is incomplete.**", "", "The local HF client reports `LocalTokenNotFoundError`. No job has been created and actual cost is **$0**." if not state else "Read `results/pilot/job-state.json` and the saved events for the partial run. Do not treat partial coverage as a completed 50-problem comparison.", "", "Pilot authorization is already recorded. Authentication is the missing prerequisite. Run `hf auth login` locally with Jobs permission. Never paste a token into chat or source files.", "", "The prepared run freezes 50 GSM8K questions and a distinct 32-question throughput workload. It sweeps concurrency 8, 16, and 32, five interleaved rounds each, with 128-token caps. It then uses the fastest error-free level with throughput CV at most 20% for the 50 scored requests at each of passes 3, 1, and 6. Scored requests retain the 8,192-token cap. Shared caches and speculative decoding are disabled.", "", "Accuracy, reasoning tokens, answer tokens, measured throughput, peak GPU memory, and GPU wall time are **not measured**. The cookbook's 84.0% and 88.5% remain external references, not pilot results."]
    else:
        lines += [f"Selected concurrency: **{observed['selected_concurrency']}**. Peak GPU memory observed: **{observed.get('peak_gpu_memory_mib')} MiB**, sampled every 0.5 seconds. This is device memory in use, including reserved pools, rather than a tensor-only allocation peak.", "", "| Passes | Correct | Accuracy, Wilson 95% CI | Mean reasoning tokens | Mean answer tokens | Aggregate tokens/s | Batch wall seconds |", "| --- | ---: | --- | ---: | ---: | ---: | ---: |"]
        for p in [1, 3, 6]:
            x = per_pass[p]
            ci = x["wilson_95"]
            lines.append(f"| {p} | {x['correct']}/50 | {100*x['accuracy']:.1f}% [{100*ci[0]:.1f}, {100*ci[1]:.1f}] | {x['mean_reasoning_tokens']:.1f} | {x['mean_answer_tokens']:.1f} | {x['aggregate_tokens_per_second']:.1f} | {x['wall_seconds']:.2f} |")
        lines += ["", "These are reference-grader scores. The supplementary boxed-numeric-scalar diagnostic scores 50/50 at all three pass counts. The reference deductions come from unit and currency formatting; see REPORT.md and grading-provenance.json for interpretation.", "", "Throughput includes prefill, scheduling, streamed responses, and final batch draining. It is aggregate generated tokens per elapsed batch second. Channel counts retokenize the parsed reasoning and answer independently; each output retains its token-count remainder. The microbenchmark uses short completions, so its winning setting is not proof of optimal throughput on long hard-domain outputs.", ""]
        for p, reference in [(1, 0.84), (3, 0.885)]:
            low, high = per_pass[p]["wilson_95"]
            lines.append(f"The {p}-pass Wilson interval {'contains' if low <= reference <= high else 'does not contain'} the cookbook reference of {100*reference:.1f}%. This 50-problem comparison is a rough check, not an exact reproduction.")
        lines += ["", f"Total worker wall time: {observed['total_worker_seconds']:.2f} seconds. Job submission-to-terminal cost upper bound: ${pilot_cost_upper:.4f}.", "", cost_method]
    lines += ["", "## Full-study cost scenarios", "", f"Basis: **{method}**. These projections retain uncertainty in output lengths outside GSM8K, cache sharing, and unmeasured pass counts. They include 25 extra compute-budget-control completions per retained domain, charged at their full output cap. The original plan compares passes 1 and 6. Trimmed plans compare passes 1 and 5, respecting the restriction of pass 6 to math. No full run is approved.", "", "| Plan | Generations | GPU hours | GPU cost | Total with CPU and contingency |", "| --- | ---: | ---: | ---: | ---: |"]
    for x in projections:
        lines.append(f"| {x['name']} | {x['generations']:,} | {x['gpu_hours']:.2f} | ${x['gpu_usd']:.2f} | ${x['total_usd']:.2f} |")
    lines += ["", f"The full-study ceiling is the smaller of $18 and $20 minus actual pilot spend. The current computed allowance is ${allowed_full_budget:.2f}.", "", "The recommended smaller-math-subset option retains 60 hard-reasoning problems along with GSM8K 200, MATH 100, and HumanEval 164. REPORT.md and recommended-full-plan.json contain the complete matrix, 25%-longer-decode sensitivity, and caveats.", "", "Do not launch the full study from these estimates. A separate approval is required. Source artifacts, IDs, and prompt hashes are in `data/subset-manifest.json`; per-output records are recovered under `results/pilot/`.", "", "The [SGLang cookbook](https://docs.sglang.io/cookbook/autoregressive/ThinkingMachines/Inkling-2-Mini) supplies the GSM8K reference results. This study always uses the varloop research checkpoint. It does not measure shipped Inkling 2 Mini."]
    (OUT / "metrics.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"status": status, "pilot_cost_approx_usd": cost_approx, "pilot_complete": complete, "full_run_authorized": False}))


if __name__ == "__main__":
    main()
