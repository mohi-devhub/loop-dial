#!/usr/bin/env python3
"""Calculate budget sensitivity from declared assumptions. No network or GPU."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def depth_ratio(passes):
    return (12 + 12 * passes) / 48


def main():
    plan = json.loads((ROOT / "study-plan.json").read_text())
    budget = plan["budget"]
    domains = plan["datasets"]
    problems = sum(d["count"] for d in domains)
    tokens_per_setting = sum(d["count"] * d["assumed_mean_output_tokens"] for d in domains)
    repeat = plan["additional_repeat_runs"]
    extra_runs = len(repeat["passes"]) * repeat["runs_per_pass_count"]
    weighted_settings = sum(depth_ratio(s["passes"]) for s in plan["settings"])
    weighted_settings += sum(depth_ratio(p) for p in repeat["passes"]) * repeat["runs_per_pass_count"]
    pilot = plan["pilot"]
    pilot_weight = sum(depth_ratio(p) for p in pilot["passes"])
    pilot_tokens = pilot["count"] * domains[0]["assumed_mean_output_tokens"] * pilot_weight
    matched = plan["compute_matched"]
    matched_tokens = matched["count_per_domain"] * sum(min(d["assumed_mean_output_tokens"], matched["pass6_max_tokens"]) for d in domains) * depth_ratio(6)
    expected_tokens = tokens_per_setting * weighted_settings + pilot_tokens + matched_tokens
    max_tokens = problems * weighted_settings * plan["sampling"]["max_tokens"]
    max_tokens += pilot["count"] * pilot_weight * plan["sampling"]["max_tokens"]
    max_tokens += matched["count_per_domain"] * len(domains) * matched["pass6_max_tokens"] * depth_ratio(6)
    scenarios = []
    for throughput in budget["assumed_three_pass_equivalent_tokens_per_second"]:
        hours = expected_tokens / throughput / 3600 + budget["assumed_total_gpu_overhead_hours"]
        gpu_cost = hours * budget["hf_gpu_hourly_usd"]
        scenarios.append({"assumed_3pass_equivalent_tokens_per_second": throughput, "gpu_hours": hours, "gpu_usd": gpu_cost, "usd_with_cpu_and_contingency": gpu_cost + budget["modal_cpu_allocation_usd"] + budget["contingency_usd"]})
    available_decode_hours = budget["hf_gpu_allocation_usd"] / budget["hf_gpu_hourly_usd"] - budget["assumed_total_gpu_overhead_hours"]
    result = {
        "kind": "estimate_not_measurement",
        "problems_per_setting": problems,
        "main_generations": problems * len(plan["settings"]),
        "additional_repeat_generations": problems * extra_runs,
        "pilot_generations": pilot["count"] * len(pilot["passes"]),
        "additional_compute_matched_generations": matched["count_per_domain"] * len(domains),
        "total_generations": problems * (len(plan["settings"]) + extra_runs) + pilot["count"] * len(pilot["passes"]) + matched["count_per_domain"] * len(domains),
        "assumed_3pass_equivalent_output_tokens": expected_tokens,
        "max_3pass_equivalent_output_tokens": max_tokens,
        "minimum_assumed_3pass_equivalent_tokens_per_second_for_gpu_allocation": expected_tokens / available_decode_hours / 3600,
        "scenarios": scenarios,
        "assumptions": ["Output lengths do not change with pass count.", "Decode cost scales with physical layer visits.", "Total overhead includes downloads, startup, graph capture, prefill, timing probes, and transitions.", "Pilot outputs are charged again even if reusable.", "Three repeat runs means three additional runs per selected pass count.", "Shared KV saves memory but is assigned no speed benefit.", "Provider prices and hardware must be rechecked before approval is used."]
    }
    path = ROOT / "evidence" / "phase0" / "budget-estimate.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
