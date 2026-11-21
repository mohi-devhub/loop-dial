#!/usr/bin/env python3
"""Build publication tables and repeat comparisons from saved responses only."""

from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re

from bs4 import BeautifulSoup
import numpy as np

from analyze_full import BOOTSTRAPS, SEED, describe, indices, paired, read_jsonl
from pilot_common import wilson


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/publication"
CARD_URL = "https://thinkingmachines.ai/model-card/tml-d24-varloop-research/"
LABEL = "thinkingmachines/TML-d24-varloop-research (varloop research checkpoint)"


def training_status(passes):
    return "untrained" if passes == 6 else "post-training depth" if passes == 3 else "midtraining only"


def extract_card(path):
    content = path.read_bytes()
    soup = BeautifulSoup(content, "html.parser")
    text = soup.get_text(" ", strip=True)
    assert "1:2:6:2:1" in text and "post-trained with 3 passes" in text
    wanted = ["DeepSWE v1.1", "GPQA Diamond", "HLE (text only)", "SimpleQA Verified", "AA-Omniscience v1.1 (Public)"]
    rows = []
    for title in soup.select(".chart-title"):
        name = title.get_text(strip=True)
        if name not in wanted:
            continue
        chart = title.find_next(class_="chartscatter")
        label = chart["aria-label"]
        if name.startswith("AA-") and "(accuracy)" not in label:
            continue
        research_text = label.split("thinkingmachines/TML-d24-varloop-research:", 1)[1]
        values = {int(p): float(v) for p, v in re.findall(r"([1-5]) pass(?:es)?, ([0-9.]+)%", research_text)}
        assert set(values) == set(range(1, 6)), label
        rows.append({"benchmark": name, "publisher_percent_by_pass": values, "source": CARD_URL, "model": "thinkingmachines/TML-d24-varloop-research", "source_kind": "publisher report, not Loop Dial measurements"})
    assert len(rows) == len(wanted)
    return {"source": CARD_URL, "html_sha256": hashlib.sha256(content).hexdigest(), "midtraining_passes": [1, 2, 3, 4, 5], "midtraining_sampling_ratio": [1, 2, 6, 2, 1], "posttraining_passes": 3, "publisher_scores": rows, "fixed_inkling_2_mini_series_included": False, "our_knowledge_control_run": False}


def result_row(rows, event, expected, level=None):
    first = rows[0]
    summary = describe(rows, event if level is None else None, expected)
    correct = summary["correct"]
    request_seconds = sum(r["request_wall_seconds"] for r in rows if not r.get("error"))
    return {"checkpoint_label": LABEL, "domain": first["domain"], "math_level": level, "passes": first["passes"], "cache": "shared" if first["share_cache"] else "separate", "repeat": first["repeat"], "training_status": training_status(first["passes"]), **summary, "request_seconds_per_correct": request_seconds / correct if correct else None, "gpu_wall_cost_status": "measured whole-domain batch" if level is None else "not identifiable for this level in a mixed concurrent batch", "isolated_level_gpu_seconds_per_correct": None}


def repeated_pairs(groups):
    results = []
    for domain in ["math", "humaneval"]:
        lo = [groups[(domain, 1, False, r)] for r in range(3)]
        hi = [groups[(domain, 3, False, r)] for r in range(3)]
        ids = sorted(set.intersection(*(set(g) for g in lo + hi)))
        ids = [i for i in ids if all(g[i].get("correct") is not None and not g[i].get("error") for g in lo + hi)]
        assert len(ids) == (100 if domain == "math" else 164)
        per_run = [{"repeat": r, **paired({i: lo[r][i] for i in ids}, {i: hi[r][i] for i in ids})} for r in range(3)]
        rng = np.random.default_rng(SEED)
        problem_indices = indices([lo[0][i] for i in ids], rng)
        run_indices = rng.integers(0, 3, size=(BOOTSTRAPS, 3))
        metrics = {}
        for metric in ["correct", "reasoning_tokens"]:
            before = np.array([[g[i][metric] for i in ids] for g in lo], dtype=float)
            after = np.array([[g[i][metric] for i in ids] for g in hi], dtype=float)
            delta = after - before
            boot = delta[run_indices[:, :, None], problem_indices[:, None, :]].mean(axis=(1, 2))
            metrics[metric] = {"mean_difference": float(delta.mean()), "hierarchical_paired_95": np.percentile(boot, [2.5, 97.5]).tolist()}
        results.append({"domain": domain, "paired_problem_count": len(ids), "run_count": 3, "per_run": per_run, "hierarchical_paired_effects": metrics, "method": "Match the same tasks across all six cells. Resample runs and problems; preserve MATH levels. McNemar is reported per run; repeated responses are not pooled as independent tasks."})
    return results


def repeated_token_cis(groups):
    results = []
    for domain in ["math", "humaneval"]:
        for passes in [1, 3]:
            runs = [groups[(domain, passes, False, r)] for r in range(3)]
            ids = sorted(set.intersection(*(set(g) for g in runs)))
            rng = np.random.default_rng(SEED)
            problems = indices([runs[0][i] for i in ids], rng)
            run_indices = rng.integers(0, 3, size=(BOOTSTRAPS, 3))
            values = np.array([[g[i]["reasoning_tokens"] for i in ids] for g in runs], dtype=float)
            boot = values[run_indices[:, :, None], problems[:, None, :]].mean(axis=(1, 2))
            results.append({"domain": domain, "passes": passes, "paired_n": len(ids), "per_run_mean_reasoning_tokens": values.mean(axis=1).tolist(), "mean_reasoning_tokens": float(values.mean()), "hierarchical_reasoning_mean_95": np.percentile(boot, [2.5, 97.5]).tolist()})
    return results


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    analysis = json.loads((ROOT / "results/full/analysis.json").read_text())
    rows = read_jsonl(ROOT / "results/full/scored-outputs.jsonl")
    assert len(rows) == 4734
    groups = defaultdict(dict)
    phases = defaultdict(list)
    for row in rows:
        groups[(row["domain"], row["passes"], row["share_cache"], row["repeat"])][row["id"]] = row
        phases[row["phase"]].append(row)
    events = {e["phase"]: e for e in read_jsonl(ROOT / "results/full/events.jsonl") if e["kind"] == "batch" and not e["phase"].startswith("warmup-")}
    full_results = []
    for condition in analysis["conditions"]:
        phase = condition["phase"]
        selected = phases[phase]
        full_results.append(result_row(selected, events[phase], condition["expected_n"]))
        if condition["domain"] == "math":
            for level in range(1, 6):
                subset = [r for r in selected if r["level"] == level]
                full_results.append(result_row(subset, None, 20 if condition["repeat"] else 40, level))
    level_comparisons = []
    for passes in [2, 3, 4, 5, 6]:
        for level in range(1, 6):
            low = {i: r for i, r in groups[("math", 1, False, 0)].items() if r["level"] == level}
            high = {i: r for i, r in groups[("math", passes, False, 0)].items() if r["level"] == level}
            level_comparisons.append({"level": level, "from_passes": 1, "to_passes": passes, **paired(low, high)})
    knowledge = None
    knowledge_path = ROOT / "results/knowledge/analysis.json"
    if knowledge_path.exists():
        knowledge = json.loads(knowledge_path.read_text())
        assert knowledge["scored_outputs"] == 600 and knowledge["distinct_questions"] == 200
        saved = read_jsonl(ROOT / "results/knowledge/scored-outputs.jsonl")
        knowledge_events = {e["passes"]: e for e in read_jsonl(ROOT / "results/knowledge/events.jsonl") if e["kind"] == "batch" and not e["phase"].startswith("warmup-")}
        for passes in [1, 3, 5]:
            selected = [r for r in saved if r["passes"] == passes]
            for row in selected:
                row["api_reasoning_tokens"] = row["usage"].get("reasoning_tokens")
            full_results.append(result_row(selected, knowledge_events[passes], 200))
    card = extract_card(ROOT / "evidence/publication-audit/model-card.html")
    card["our_knowledge_control_run"] = knowledge is not None
    (OUT / "model-card-context.json").write_text(json.dumps(card, indent=2) + "\n")
    level5 = [r for r in full_results if r["domain"] == "math" and r["math_level"] == 5 and r["repeat"] == 0 and r["cache"] == "separate"]
    result = {"checkpoint_label": LABEL, "source_output_count": len(rows), "full_results": full_results, "math_level_comparisons": level_comparisons, "repeat_paired_comparisons": repeated_pairs(groups), "repeat_reasoning_cis": repeated_token_cis(groups), "level5_ceiling": level5, "knowledge_control": {"dataset": "google/simpleqa-verified", "passes": [1, 3, 5], "status": "not run", "observed_scores": None, "flatness_assessed_from_our_outputs": False}, "timing_definition": "request_seconds_per_correct sums measured request latencies, including failures, and divides by correct count. Requests overlap at C32. Whole-domain batch GPU seconds per correct are separately measured. Isolated level GPU wall times were never measured and are left null; no proportional GPU allocation is fabricated."}
    if knowledge:
        result["source_output_count"] += knowledge["scored_outputs"]
        result["knowledge_control"].update(status="complete", observed_scores=knowledge["conditions"], paired_accuracy_assessed=True, equivalence_established=False, source="results/knowledge/analysis.json")
    (OUT / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    fields = sorted(set().union(*(r.keys() for r in full_results)))
    with (OUT / "full-results.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(full_results)
    print(json.dumps({"results_rows": len(full_results), "level_comparisons": len(level_comparisons), "repeat_paired_domains": 2, "inference_runs_launched": 0}))


if __name__ == "__main__":
    main()
