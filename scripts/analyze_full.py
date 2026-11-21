#!/usr/bin/env python3
"""Paired accuracy, token, difficulty, timing, and repeat-noise analysis."""

from collections import defaultdict
import itertools
import gzip
import json
import math
from pathlib import Path

import numpy as np

from pilot_common import wilson


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/full"
BOOTSTRAPS = 10000
SEED = 271828
PRIMARY_FAMILY_SIZE = 3


def read_jsonl(path):
    source = path if path.exists() else path.with_suffix(path.suffix + ".gz")
    if not source.exists():
        return []
    opener = gzip.open if source.suffix == ".gz" else open
    with opener(source, "rt") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def indices(rows, rng):
    strata = defaultdict(list)
    for index, row in enumerate(rows):
        stratum = row.get("level") if row["domain"] == "math" else row.get("task") if row["domain"] == "bbh" else 0
        strata[stratum].append(index)
    return np.concatenate([rng.choice(group, size=(BOOTSTRAPS, len(group)), replace=True) for group in strata.values()], axis=1)


def mcnemar(before, after):
    loss = sum(bool(a) and not bool(b) for a, b in zip(before, after))
    gain = sum(not bool(a) and bool(b) for a, b in zip(before, after))
    discordant = loss + gain
    p = min(1, 2 * sum(math.comb(discordant, i) for i in range(min(loss, gain) + 1)) / 2 ** discordant) if discordant else 1.0
    return {"gains": gain, "losses": loss, "discordant": discordant, "exact_two_sided_p": p}


def paired(a, b):
    ids = sorted(set(a) & set(b))
    ids = [i for i in ids if not a[i].get("error") and not b[i].get("error")]
    if not ids:
        return {"n": 0}
    rows = [a[i] for i in ids]
    sampled = indices(rows, np.random.default_rng(SEED))
    scored_ids = [i for i in ids if a[i].get("correct") is not None and b[i].get("correct") is not None]
    result = {"n": len(ids), "n_accuracy_pairs": len(scored_ids)}
    if scored_ids:
        left = np.array([a[i]["correct"] for i in scored_ids], dtype=float)
        right = np.array([b[i]["correct"] for i in scored_ids], dtype=float)
        differences = right - left
        accuracy_sampled = indices([a[i] for i in scored_ids], np.random.default_rng(SEED))
        result.update(accuracy_difference=float(differences.mean()), accuracy_difference_95=np.percentile(differences[accuracy_sampled].mean(axis=1), [2.5, 97.5]).tolist(), mcnemar=mcnemar(left, right))
        result["gained_ids"] = [i for i in scored_ids if not a[i]["correct"] and b[i]["correct"]]
        result["lost_ids"] = [i for i in scored_ids if a[i]["correct"] and not b[i]["correct"]]
    for metric in ["reasoning_tokens", "completion_tokens"]:
        x = np.array([a[i][metric] for i in ids], dtype=float)
        y = np.array([b[i][metric] for i in ids], dtype=float)
        diffs = y - x
        ratios = y[sampled].mean(axis=1) / np.maximum(x[sampled].mean(axis=1), 1e-12) - 1
        result[metric] = {"mean_difference": float(diffs.mean()), "difference_95": np.percentile(diffs[sampled].mean(axis=1), [2.5, 97.5]).tolist(), "relative_mean_change": float(y.mean() / x.mean() - 1) if x.mean() else None, "relative_change_95": np.percentile(ratios, [2.5, 97.5]).tolist()}
    result["reasoning_sensitivity"] = {}
    for name, keep in [("both_correct", lambda i: a[i].get("correct") is True and b[i].get("correct") is True), ("neither_truncated", lambda i: a[i].get("finish_reason") != "length" and b[i].get("finish_reason") != "length")]:
        selected = [i for i in ids if keep(i)]
        if not selected:
            continue
        sample = indices([a[i] for i in selected], np.random.default_rng(SEED))
        x = np.array([a[i]["reasoning_tokens"] for i in selected], dtype=float)
        y = np.array([b[i]["reasoning_tokens"] for i in selected], dtype=float)
        delta = y - x
        result["reasoning_sensitivity"][name] = {"n": len(selected), "mean_before": float(x.mean()), "mean_after": float(y.mean()), "mean_difference": float(delta.mean()), "difference_95": np.percentile(delta[sample].mean(axis=1), [2.5, 97.5]).tolist(), "relative_mean_change": float(y.mean() / x.mean() - 1) if x.mean() else None}
    return result


def describe(rows, event, expected_count):
    valid = [r for r in rows if not r.get("error")]
    scored = [r for r in valid if r.get("correct") is not None]
    correct = sum(bool(r["correct"]) for r in scored)
    seconds = event["summary"]["wall_seconds"] if event else None
    result = {"n_outputs": len(rows), "expected_n": expected_count, "n_valid_inference": len(valid), "n_scored": len(scored), "correct": correct, "complete": len(scored) == expected_count, "accuracy": correct / len(scored) if scored else None, "unknown_scores": len(rows) - len(scored), "inference_errors": len(rows) - len(valid), "truncations": sum(r.get("finish_reason") == "length" for r in valid), "wilson_95": wilson(correct, len(scored)), "batch_wall_seconds": seconds, "gpu_seconds_per_correct": seconds / correct if seconds is not None and correct else None, "inference_usd_per_correct": seconds * 2.75 / 3600 / correct if seconds is not None and correct else None}
    result.update(missing_outputs=expected_count - len(rows), correct_answers_per_gpu_second=correct / seconds if seconds and scored else None, amortized_gpu_seconds_per_problem=seconds / len(valid) if seconds and valid else None, peak_gpu_memory_mib=event.get("gpu", {}).get("peak_gpu_memory_mib") if event else None)
    if scored:
        sampled = indices(scored, np.random.default_rng(SEED))
        scores = np.array([r["correct"] for r in scored], dtype=float)
        result["stratified_bootstrap_accuracy_95"] = np.percentile(scores[sampled].mean(axis=1), [2.5, 97.5]).tolist()
        raw = [r["raw_string_match"] for r in scored if r.get("raw_string_match") is not None]
        result["raw_string_match_accuracy"] = float(np.mean(raw)) if raw else None
    for metric in ["reasoning_tokens", "api_reasoning_tokens", "answer_tokens", "completion_tokens", "request_wall_seconds", "first_text_seconds", "effective_decode_seconds_per_token"]:
        values = [r[metric] for r in valid if r.get(metric) is not None]
        result["mean_" + metric] = float(np.mean(values)) if values else None
        result["median_" + metric] = float(np.median(values)) if values else None
    tokens = sum(r["completion_tokens"] for r in valid)
    result["tokens_per_correct"] = tokens / correct if correct else None
    result["aggregate_tokens_per_second"] = tokens / seconds if seconds else None
    return result


def difficulty(groups):
    summaries = []
    for passes in range(1, 7):
        group = groups.get(("math", passes, False, 0), {})
        for level in range(1, 6):
            rows = [r for r in group.values() if r["level"] == level and not r.get("error")]
            if rows:
                scored = [r for r in rows if r.get("correct") is not None]
                summaries.append({"passes": passes, "level": level, "n": len(rows), "accuracy": float(np.mean([r["correct"] for r in scored])) if scored else None, "mean_reasoning_tokens": float(np.mean([r["reasoning_tokens"] for r in rows])), "median_reasoning_tokens": float(np.median([r["reasoning_tokens"] for r in rows]))})
    effects = []
    for lo, hi in [(1, 3), (3, 4), (3, 5), (3, 6)]:
        a = groups.get(("math", lo, False, 0), {})
        b = groups.get(("math", hi, False, 0), {})
        ids = sorted(set(a) & set(b))
        ids = [i for i in ids if not a[i].get("error") and not b[i].get("error")]
        if not ids:
            continue
        resamples = indices([a[i] for i in ids], np.random.default_rng(SEED))
        x = np.array([a[i]["reasoning_tokens"] for i in ids], dtype=float)
        y = np.array([b[i]["reasoning_tokens"] for i in ids], dtype=float)
        levels = np.array([a[i]["level"] for i in ids])
        result = {"from_passes": lo, "to_passes": hi, "levels": []}
        for level in range(1, 6):
            mask = levels == level
            if not mask.any():
                continue
            selected = resamples[:, levels[resamples[0]] == level]
            delta = y - x
            ratio = y[selected].mean(axis=1) / np.maximum(x[selected].mean(axis=1), 1e-12) - 1
            result["levels"].append({"level": level, "n": int(mask.sum()), "mean_token_difference": float(delta[mask].mean()), "difference_95": np.percentile(delta[selected].mean(axis=1), [2.5, 97.5]).tolist(), "relative_change": float(y[mask].mean() / x[mask].mean() - 1), "relative_change_95": np.percentile(ratio, [2.5, 97.5]).tolist()})
        easy = np.where(levels <= 2)[0]
        hard = np.where(levels >= 4)[0]
        if len(easy) and len(hard):
            ei = resamples[:, levels[resamples[0]] <= 2]
            he = resamples[:, levels[resamples[0]] >= 4]
            rd = (y[he].mean(axis=1) / x[he].mean(axis=1) - 1) - (y[ei].mean(axis=1) / x[ei].mean(axis=1) - 1)
            absolute = (y - x)[he].mean(axis=1) - (y - x)[ei].mean(axis=1)
            result["hard_minus_easy_relative_change"] = float((y[hard].mean() / x[hard].mean() - 1) - (y[easy].mean() / x[easy].mean() - 1))
            result["hard_minus_easy_relative_95"] = np.percentile(rd, [2.5, 97.5]).tolist()
            result["hard_minus_easy_absolute_difference"] = float((y - x)[hard].mean() - (y - x)[easy].mean())
            result["hard_minus_easy_absolute_95"] = np.percentile(absolute, [2.5, 97.5]).tolist()
        effects.append(result)
    return {"level_means": summaries, "paired_effects": effects, "definition": "Easy levels 1–2, hard levels 4–5. Negative hard-minus-easy relative change indicates stronger proportional shortening on hard tasks."}


def repeat_noise(groups):
    results = []
    for domain in ["math", "humaneval"]:
        for passes in [1, 3]:
            runs = [groups.get((domain, passes, False, r), {}) for r in [0, 1, 2]]
            ids = sorted(set.intersection(*(set(g) for g in runs)))
            ids = [i for i in ids if all(g[i].get("correct") is not None for g in runs)]
            if not ids:
                continue
            values = np.array([[g[i]["correct"] for i in ids] for g in runs], dtype=float)
            rng = np.random.default_rng(SEED)
            samples = indices([runs[0][i] for i in ids], rng)
            run_indices = rng.integers(0, 3, size=(BOOTSTRAPS, 3))
            boot = values[run_indices[:, :, None], samples[:, None, :]].mean(axis=(1, 2))
            accuracies = values.mean(axis=1)
            results.append({"domain": domain, "passes": passes, "paired_n": len(ids), "run_accuracies": accuracies.tolist(), "accuracy_range_pp": float((accuracies.max() - accuracies.min()) * 100), "accuracy_std_pp": float(accuracies.std(ddof=1) * 100), "hierarchical_accuracy_95": np.percentile(boot, [2.5, 97.5]).tolist(), "score_flips": [int(np.sum(values[0] != values[r])) for r in [1, 2]], "exact_output_agreement": [sum((runs[0][i]["answer"], runs[0][i]["reasoning"]) == (runs[r][i]["answer"], runs[r][i]["reasoning"]) for i in ids) / len(ids) for r in [1, 2]]})
    return results


def observed_compute_matches(groups, conditions):
    results = []
    for domain in ["math", "gsm8k", "humaneval", "bbh"]:
        for low, high in [(1, 3), (1, 5), (3, 5), (3, 6)]:
            a = groups.get((domain, low, False, 0), {})
            b = groups.get((domain, high, False, 0), {})
            common = sorted(set(a) & set(b))
            for tolerance in [0.05, 0.10, 0.20]:
                ids = []
                for i in common:
                    if a[i].get("error") or b[i].get("error"):
                        continue
                    ca = a[i]["completion_tokens"] * (low + 1)
                    cb = b[i]["completion_tokens"] * (high + 1)
                    if ca and abs(cb / ca - 1) <= tolerance and a[i]["reasoning_tokens"] > b[i]["reasoning_tokens"]:
                        ids.append(i)
                if ids:
                    results.append({"domain": domain, "from_passes": low, "to_passes": high, "relative_compute_tolerance": tolerance, "ids": ids, **paired({i: a[i] for i in ids}, {i: b[i] for i in ids})})
    batch_tradeoffs = []
    for domain in ["math", "gsm8k", "humaneval", "bbh"]:
        rows = sorted([r for r in conditions if r["domain"] == domain and r["repeat"] == 0 and not r["share_cache"] and r["batch_wall_seconds"] and r["n_outputs"] == r["expected_n"]], key=lambda r: r["passes"])
        for low, high in itertools.combinations(rows, 2):
            wall_change = high["batch_wall_seconds"] / low["batch_wall_seconds"] - 1
            proxy_change = high["mean_completion_tokens"] * (high["passes"] + 1) / (low["mean_completion_tokens"] * (low["passes"] + 1)) - 1
            batch_tradeoffs.append({"domain": domain, "from_passes": low["passes"], "to_passes": high["passes"], "from_batch_seconds": low["batch_wall_seconds"], "to_batch_seconds": high["batch_wall_seconds"], "batch_wall_relative_change": wall_change, "within_10_percent_batch_wall_time": abs(wall_change) <= 0.10, "layer_token_proxy_relative_change": proxy_change, "reasoning_relative_change": high["mean_reasoning_tokens"] / low["mean_reasoning_tokens"] - 1, "accuracy_difference": high["accuracy"] - low["accuracy"] if high["accuracy"] is not None and low["accuracy"] is not None else None})
    return {"method": "Observational same-problem pairs with fewer written reasoning tokens at higher depth and completion_tokens*(passes+1) within 5/10/20%. The proxy counts repeated transformer layers (12 outer + 12 per pass); it excludes prefill, KV memory, and scheduling. Selection uses realized output length, so these are descriptive subsets, not causal compute-controlled experiments. Whole-cohort batch tradeoffs are also retained for every observed main-run pass pair, without selecting individual problems by outcome; a within-10%-wall-time flag marks naturally similar observed batch budgets, not a controlled budget intervention.", "comparisons": results, "batch_tradeoffs": batch_tradeoffs}


def bbh_task_breakdown(groups):
    result = []
    for passes in [1, 3, 5]:
        rows = groups.get(("bbh", passes, False, 0), {})
        for task in sorted({r["task"] for r in rows.values()}):
            selected = [r for r in rows.values() if r["task"] == task and r.get("correct") is not None]
            result.append({"task": task, "passes": passes, "n_scored": len(selected), "correct": sum(r["correct"] for r in selected), "truncations": sum(r["finish_reason"] == "length" for r in selected), "mean_reasoning_tokens": float(np.mean([r["reasoning_tokens"] for r in selected])) if selected else None})
    return result


def main():
    config = json.loads((ROOT / "full-config.json").read_text())
    rows = read_jsonl(OUT / "scored-outputs.jsonl")
    assert len({r["phase"] + ":" + r["id"] for r in rows}) == len(rows)
    scores = {x["phase"] + ":" + x["id"]: x for x in rows}
    groups = defaultdict(dict)
    merged = []
    for row in rows:
        score = scores.get(row["phase"] + ":" + row["id"], {})
        result = {**row, **{k: v for k, v in score.items() if k not in ["key", "wall_seconds", "domain", "id"]}}
        result["api_reasoning_tokens"] = row.get("usage", {}).get("reasoning_tokens")
        result["correct"] = None if score.get("infrastructure_error") or row.get("error") else score.get("correct")
        merged.append(result)
        groups[(row["domain"], row["passes"], row["share_cache"], row["repeat"])][row["id"]] = result
    events = read_jsonl(OUT / "events.jsonl")
    batches = {e["phase"]: e for e in events if e["kind"] == "batch" and not e["phase"].startswith("warmup-")}
    conditions = []
    for case in config["cases"]:
        passes, shared, repeat = case["passes"], case["share_cache"], case["repeat"]
        for domain in case["domains"]:
            group = groups.get((domain, passes, shared, repeat), {})
            phase = case["key"] + "--" + domain
            expected = config["repeat_counts"][domain] if repeat else config["domain_counts"][domain]
            regime = "beyond the trained range" if passes == 6 else "midtraining range, not RL'd" if passes in [4, 5] else "RL training depth" if passes == 3 else "midtraining range"
            conditions.append({"checkpoint_label": config["checkpoint_label"], "model": config["model"], "revision": config["revision"], "phase": phase, "domain": domain, "passes": passes, "share_cache": shared, "repeat": repeat, "training_regime": regime, **describe(list(group.values()), batches.get(phase), expected)})
    comparisons = []
    for domain, passes in config["main_passes"].items():
        pairs = set(zip(passes, passes[1:])) | {(3, p) for p in passes if p > 3}
        if 1 in passes and 3 in passes:
            pairs.add((1, 3))
        for a, b in sorted(pairs):
            comparisons.append({"domain": domain, "from_passes": a, "to_passes": b, "comparison": "separate", **paired(groups.get((domain, a, False, 0), {}), groups.get((domain, b, False, 0), {}))})
    for domain in config["shared_domains"]:
        for p in config["shared_passes"]:
            comparisons.append({"domain": domain, "from_passes": p, "to_passes": p, "comparison": "shared_vs_separate", **paired(groups.get((domain, p, False, 0), {}), groups.get((domain, p, True, 0), {}))})
    primary = [x for x in comparisons if x["domain"] == "math" and x["comparison"] == "separate" and x["from_passes"] == 3 and x["to_passes"] in [4, 5, 6] and x.get("n_accuracy_pairs")]
    ordered = sorted(primary, key=lambda x: x["mcnemar"]["exact_two_sided_p"])
    last = 0
    for rank, item in enumerate(ordered):
        value = min(1, max(last, item["mcnemar"]["exact_two_sided_p"] * (PRIMARY_FAMILY_SIZE - rank)))
        item["mcnemar"]["holm_p_for_math_3_vs_4_5_6"] = value
        last = value
    result = {"checkpoint_label": config["checkpoint_label"], "expected_inference_outputs": json.loads((OUT / "forecast.json").read_text())["selected"]["generation_count"], "n_outputs": len(rows), "n_scored": sum(r["correct"] is not None for r in merged), "conditions": conditions, "paired_comparisons": comparisons, "math_difficulty": difficulty(groups), "repeat_noise": repeat_noise(groups), "bbh_tasks": bbh_task_breakdown(groups), "observational_compute_matches": observed_compute_matches(groups, conditions), "statistical_method": {"bootstrap_resamples": BOOTSTRAPS, "seed": SEED, "mcnemar": "Exact two-sided binomial test on paired discordant counts", "primary_multiple_comparisons": "Holm over MATH 3-versus-4, 3-versus-5, 3-versus-6; other comparisons exploratory", "math_accuracy": "Equal level weighting, 40 per level; stratified problem bootstrap", "repeat_note": "Three observations per repeated setting; use the shared 100-MATH/164-code subset, never pool repeated problems as independent samples."}}
    (OUT / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"outputs": len(rows), "scored": result["n_scored"], "conditions": len(conditions)}))


if __name__ == "__main__":
    main()
