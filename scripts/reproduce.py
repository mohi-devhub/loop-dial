#!/usr/bin/env python3
"""Regenerate published analysis and figures with networking disabled."""

import json
import math
from pathlib import Path
import runpy
import socket
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def no_network(*args, **kwargs):
    raise RuntimeError("CPU reproduction forbids network access and model/API calls")


def numbers(value, path=""):
    if isinstance(value, dict):
        return {k: v for name, item in value.items() for k, v in numbers(item, path + "/" + name).items()}
    if isinstance(value, list):
        return {k: v for i, item in enumerate(value) for k, v in numbers(item, path + "/" + str(i)).items()}
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return {path: value}
    return {}


def main():
    socket.socket.connect = no_network
    socket.create_connection = no_network
    for name in ["check_pilot", "recompute_budgets", "analyze_full", "analyze_knowledge", "publication_analysis", "failure_examples", "sanity_reference", "plot_full", "plot_publication", "render_knowledge", "render_full_report", "render_thread", "render_readme", "public_cleanup"]:
        runpy.run_path(str(ROOT / f"scripts/{name}.py"), run_name="__main__")
    pairs = [("analyze_full", "results/full/analysis.json"), ("analyze_knowledge", "results/knowledge/analysis.json"), ("publication", "results/publication/analysis.json")]
    pairs += [("legacy-sanity", "results/full/gsm8k-legacy-sanity.json"), ("full-budget", "results/full/budget-report.json"), ("knowledge-budget", "results/knowledge/budget-report.json"), ("model-card-context", "results/publication/model-card-context.json"), ("pilot-summary", "results/pilot/rescored-numeric-v2-summary.json")]
    mismatches, checked = [], 0
    for reference, actual in pairs:
        expected = numbers(json.loads((ROOT / f"reference/{reference}.json").read_text()))
        observed = numbers(json.loads((ROOT / actual).read_text()))
        for key, value in expected.items():
            checked += 1
            if key not in observed or not math.isclose(value, observed[key], rel_tol=1e-12, abs_tol=1e-12):
                mismatches.append({"file": actual, "field": key, "expected": value, "observed": observed.get(key)})
    result = {"network_enabled": False, "gpu_access_used": False, "model_or_grader_calls": 0, "numeric_values_checked": checked, "mismatches": mismatches, "tolerance": 1e-12}
    (ROOT / "results/reproduction.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    if mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
