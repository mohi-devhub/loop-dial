#!/usr/bin/env python3
"""Forecast the approved matrix and apply only the user's ordered budget cuts."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def interpolate(values, passes):
    if passes in values:
        return values[passes]
    low = max(x for x in values if x < passes)
    high = min(x for x in values if x > passes)
    return values[low] + (values[high] - values[low]) * (passes - low) / (high - low)


def forecast(config):
    rows = json.loads((ROOT / "results/pilot/summary.json").read_text())["summaries"]
    pilot = {x["passes"]: x for x in rows}
    seconds_per_token = {p: interpolate({q: 1 / x["aggregate_tokens_per_second"] for q, x in pilot.items()}, p) for p in range(1, 7)}
    relative_length = {p: interpolate({q: x["mean_completion_tokens"] / pilot[3]["mean_completion_tokens"] for q, x in pilot.items()}, p) for p in range(1, 7)}
    lengths = {"gsm8k": pilot[3]["mean_completion_tokens"], "math": 3072, "humaneval": 1024, "bbh": 3072}
    cells = []
    for domain, passes in config["main_passes"].items():
        for p in passes:
            cells.append((domain, p, config["domain_counts"][domain], False, 0))
    for p in config["shared_passes"]:
        for domain in config["shared_domains"]:
            cells.append((domain, p, config["domain_counts"][domain], True, 0))
    for repeat in range(1, config["additional_repeat_runs"] + 1):
        for p in config["repeat_passes"]:
            for domain, count in config["repeat_counts"].items():
                cells.append((domain, p, count, False, repeat))
    events = [json.loads(x) for x in (ROOT / "results/pilot/events.jsonl").read_text().splitlines()]
    ready = [x for x in events if x["kind"] == "server_ready"]
    starts = len(config["execution_pass_order"]) + len(config["shared_passes"]) + config["additional_repeat_runs"] * len(config["repeat_passes"])
    overhead = ready[0]["worker_elapsed_seconds"] + (starts - 1) * sum(x["startup_seconds"] for x in ready[1:]) / len(ready[1:]) + 120
    decode = sum(n * lengths[d] * relative_length[p] * seconds_per_token[p] for d, p, n, _, _ in cells)
    gpu_hours = (decode + overhead) / 3600
    return {"generation_count": sum(x[2] for x in cells), "cells": [{"domain": d, "passes": p, "count": n, "share_cache": s, "repeat": r} for d, p, n, s, r in cells if n], "gpu_hours": gpu_hours, "startup_hours": overhead / 3600, "gpu_usd": gpu_hours * 2.75, "cpu_reserve_usd": config["cpu_reserve_usd"], "nominal_total_usd": gpu_hours * 2.75 + config["cpu_reserve_usd"], "total_if_decode_25_percent_longer_usd": (decode * 1.25 + overhead) / 3600 * 2.75 + config["cpu_reserve_usd"], "pass3_mean_output_assumptions": lengths, "seconds_per_token": seconds_per_token, "relative_length": relative_length, "server_starts": starts}


def main():
    path = ROOT / "full-config.json"
    config = json.loads(path.read_text())
    original = forecast(config)
    versions = [{"matrix": "requested", **original}]
    if original["nominal_total_usd"] > config["nominal_threshold_usd"] and config["domain_counts"]["bbh"]:
        config["domain_counts"]["bbh"] = 0
        config["budget_cuts_applied"].append("drop hard reasoning")
        versions.append({"matrix": "drop hard reasoning", **forecast(config)})
    if forecast(config)["nominal_total_usd"] > config["nominal_threshold_usd"] and config["domain_counts"]["gsm8k"] > 100:
        config["domain_counts"]["gsm8k"] = 100
        config["budget_cuts_applied"].append("reduce GSM8K to 100")
        versions.append({"matrix": "reduce GSM8K to 100", **forecast(config)})
    selected = forecast(config)
    result = {"checkpoint_label": config["checkpoint_label"], "cap_usd": 15, "nominal_threshold_usd": 13, "nominal_definition": "GPU time including startup plus CPU sandbox reserve; excludes unused contingency inside the hard cap", "assumptions": "Measured pilot rates at 1,3,6; interpolate 2,4,5. Only GSM8K lengths are measured; other domain lengths and cross-pass length ratios are assumptions. Shared-cache speed assumed unchanged. No unlisted extra inference controls.", "selected": selected, "versions": versions, "cuts_applied": config["budget_cuts_applied"]}
    out = ROOT / "results/full"
    out.mkdir(parents=True, exist_ok=True)
    (out / "forecast.json").write_text(json.dumps(result, indent=2) + "\n")
    path.write_text(json.dumps(config, indent=2) + "\n")
    print(json.dumps({k: selected[k] for k in ["generation_count", "gpu_hours", "gpu_usd", "nominal_total_usd", "total_if_decode_25_percent_longer_usd"]}))


if __name__ == "__main__":
    main()
