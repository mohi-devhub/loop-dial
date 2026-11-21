#!/usr/bin/env python3
"""Render publication-ready figures from the scored study artifact."""

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/full"
CHARTS = OUT / "charts"
NAMES = {"math": "MATH-500 · 200 stratified problems", "gsm8k": "GSM8K · 150 problems", "humaneval": "HumanEval · 164 problems", "bbh": "BBH · 60 problems across five tasks"}
COLORS = {"math": "#205a9b", "gsm8k": "#00826e", "humaneval": "#a04718", "bbh": "#7a4e9b"}
DOMAINS = list(NAMES)


def finish(fig, name):
    fig.suptitle("Loop Dial · thinkingmachines/TML-d24-varloop-research", fontsize=16, fontweight="bold", x=0.06, ha="left")
    if name == "accuracy-vs-passes":
        fig.text(0.06, 0.935, "Error bars: 95% Wilson confidence intervals. Paired tests are reported separately.", fontsize=9, color="#444444")
    if name == "accuracy-vs-latency-pareto":
        fig.text(0.06, 0.935, "Labels = passes; s = shared cache. Dotted lines: point-estimate frontier. Times exclude server startup.", fontsize=9, color="#444444")
    fig.text(0.06, 0.012, "Varloop research checkpoint · C32 · temperature 0 · 4–5: midtraining range, not RL'd · 6: beyond the trained range", fontsize=8, color="#444444")
    fig.tight_layout(rect=(0.02, 0.045, 1, 0.94), h_pad=2.5, w_pad=2.5)
    fig.savefig(CHARTS / (name + ".png"), dpi=200, facecolor="white")
    fig.savefig(CHARTS / (name + ".svg"), facecolor="white")
    plt.close(fig)


def main():
    data = json.loads((OUT / "analysis.json").read_text())
    conditions = data["conditions"]
    CHARTS.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.18, "axes.axisbelow": True})
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 8.1))
    for ax, domain in zip(axes.flat, DOMAINS):
        for shared in [False, True]:
            rows = sorted([x for x in conditions if x["domain"] == domain and x["repeat"] == 0 and x["share_cache"] == shared and x["n_scored"]], key=lambda x: x["passes"])
            if not rows:
                continue
            y = np.array([r["accuracy"] * 100 for r in rows])
            ci = np.array([r["wilson_95"] for r in rows]).T * 100
            ax.errorbar([r["passes"] + (0.06 if shared else 0) for r in rows], y, yerr=[y - ci[0], ci[1] - y], fmt="s--" if shared else "o-", color="#666666" if shared else COLORS[domain], capsize=3, label="Shared cache" if shared else "Separate caches")
        ax.set(title=NAMES[domain], xlabel="Loop passes", ylabel="Accuracy (%)", xticks=range(1, 7))
        if domain == "gsm8k":
            ax.text(0.03, 0.05, "Used primarily to measure reasoning length", transform=ax.transAxes, fontsize=8)
        ax.legend(fontsize=8)
    finish(fig, "accuracy-vs-passes")

    fig, axes = plt.subplots(2, 2, figsize=(11.2, 8.1))
    for ax, domain in zip(axes.flat, DOMAINS):
        rows = sorted([x for x in conditions if x["domain"] == domain and x["repeat"] == 0 and not x["share_cache"] and x["n_valid_inference"]], key=lambda x: x["passes"])
        for metric, label, fmt, color in [("reasoning", "Reasoning", "o-", COLORS[domain]), ("answer", "Answer", "s--", "#777777")]:
            ax.plot([r["passes"] for r in rows], [r["mean_" + metric + "_tokens"] for r in rows], fmt, label=label, color=color)
        ax.set(title=NAMES[domain], xlabel="Loop passes", ylabel="Mean output tokens", xticks=range(1, 7), ylim=(0, None))
        ax.legend(fontsize=8)
    finish(fig, "tokens-vs-passes")

    fig, axes = plt.subplots(2, 2, figsize=(11.2, 8.1))
    frontier = []
    for ax, domain in zip(axes.flat, DOMAINS):
        rows = [x for x in conditions if x["domain"] == domain and x["repeat"] == 0 and x["n_scored"] and x["batch_wall_seconds"]]
        for row in rows:
            x = row["batch_wall_seconds"] / row["n_valid_inference"]
            y = row["accuracy"] * 100
            ax.scatter(x, y, color="#666666" if row["share_cache"] else COLORS[domain], marker="s" if row["share_cache"] else "o", s=50)
            ax.annotate(str(row["passes"]) + ("s" if row["share_cache"] else ""), (x, y), xytext=(5, 5), textcoords="offset points", fontsize=9)
        efficient = []
        for row in rows:
            x = row["batch_wall_seconds"] / row["n_valid_inference"]
            dominated = any(other["accuracy"] >= row["accuracy"] and other["batch_wall_seconds"] / other["n_valid_inference"] <= x and (other["accuracy"] > row["accuracy"] or other["batch_wall_seconds"] / other["n_valid_inference"] < x) for other in rows)
            if not dominated:
                efficient.append(row)
                frontier.append({"domain": domain, "passes": row["passes"], "share_cache": row["share_cache"], "accuracy": row["accuracy"], "amortized_gpu_seconds_per_problem": x})
        efficient.sort(key=lambda r: r["batch_wall_seconds"] / r["n_valid_inference"])
        ax.plot([r["batch_wall_seconds"] / r["n_valid_inference"] for r in efficient], [r["accuracy"] * 100 for r in efficient], color=COLORS[domain], alpha=0.5, linestyle=":")
        ax.set(title=NAMES[domain], xlabel="Amortized GPU seconds per problem (C32)", ylabel="Accuracy (%)")
    finish(fig, "accuracy-vs-latency-pareto")
    (OUT / "pareto.json").write_text(json.dumps(frontier, indent=2) + "\n")

    fig, axes = plt.subplots(1, 2, figsize=(11.2, 5.0))
    levels = data["math_difficulty"]["level_means"]
    for level in range(1, 6):
        rows = sorted([r for r in levels if r["level"] == level], key=lambda x: x["passes"])
        if not rows:
            continue
        xs = [r["passes"] for r in rows]
        ys = [r["mean_reasoning_tokens"] for r in rows]
        axes[0].plot(xs, ys, "o-", label=f"Level {level}")
        axes[1].plot(xs, np.array(ys) / ys[0], "o-", label=f"Level {level}")
    axes[0].set(title="MATH reasoning by difficulty", xlabel="Loop passes", ylabel="Mean reasoning tokens", xticks=range(1, 7))
    axes[1].set(title="Relative to each level's 1-pass length", xlabel="Loop passes", ylabel="Reasoning length / 1-pass length", xticks=range(1, 7))
    for ax in axes:
        ax.legend(fontsize=8)
    finish(fig, "math-difficulty-reasoning")

    fields = sorted(set().union(*(x.keys() for x in conditions)))
    with (OUT / "metrics.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(conditions)
    print(json.dumps({"figures": 4, "formats": ["png", "svg"], "metrics": len(conditions)}))


if __name__ == "__main__":
    main()
