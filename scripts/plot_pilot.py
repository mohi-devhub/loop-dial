#!/usr/bin/env python3
"""Plot only observed pilot measurements for the varloop research checkpoint."""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/pilot"


def main():
    summary = json.loads((OUT / "summary.json").read_text())
    rows = sorted(summary["summaries"], key=lambda x: x["passes"])
    assert len(rows) == 3 and all(x["attempted"] == 50 and x["errors"] == 0 for x in rows)
    passes = np.array([x["passes"] for x in rows])
    accuracy = np.array([100 * x["accuracy"] for x in rows])
    errors = np.array([[100 * x["wilson_95"][0], 100 * x["wilson_95"][1]] for x in rows])
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5), layout="constrained")
    axes[0].errorbar(passes, accuracy, yerr=np.vstack([accuracy - errors[:, 0], errors[:, 1] - accuracy]), fmt="o", capsize=4, color="#264653", label="Reference grader, 95% CI")
    axes[0].scatter(passes, [100 * x["scalar_accuracy"] for x in rows], marker="^", facecolors="none", edgecolors="#e76f51", label="Numeric scalar")
    axes[0].set(ylabel="Accuracy (%)", ylim=(0, 105), yticks=range(0, 101, 20), title="GSM8K, 50 paired problems")
    axes[0].legend(frameon=False, loc="lower left", fontsize=8)
    axes[1].bar(passes, [x["mean_reasoning_tokens"] for x in rows], width=0.5, color="#2a9d8f", label="Reasoning")
    axes[1].bar(passes, [x["mean_answer_tokens"] for x in rows], bottom=[x["mean_reasoning_tokens"] for x in rows], width=0.5, color="#e9c46a", label="Answer")
    axes[1].set(ylabel="Mean output tokens", title="Parsed output length")
    axes[1].legend(frameon=False)
    axes[2].scatter(passes, [x["aggregate_tokens_per_second"] for x in rows], color="#264653")
    axes[2].set(ylabel="Aggregate completion tokens/second", title=f"Observed batch throughput, C={summary['selected_concurrency']}")
    for ax in axes:
        ax.set(xlabel="Loop passes", xticks=passes)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.15)
        ax.set_axisbelow(True)
    fig.suptitle("thinkingmachines/TML-d24-varloop-research · separate KV caches · temperature 0", fontsize=12)
    for extension in ["png", "svg"]:
        fig.savefig(OUT / f"pilot-curves.{extension}", dpi=200)
    plt.close(fig)
    sweep = json.loads((OUT / "throughput-summary.json").read_text())
    choices = sweep["choices"]
    fig, ax = plt.subplots(figsize=(6.3, 3.6), layout="constrained")
    for x in choices:
        ax.errorbar(x["concurrency"], x["median_tokens_per_second"], yerr=[[x["median_tokens_per_second"] - x["min_tokens_per_second"]], [x["max_tokens_per_second"] - x["median_tokens_per_second"]]], fmt="o", capsize=5, color="#2a9d8f" if x["stable"] else "#e76f51")
    ax.set(xlabel="Concurrent requests", ylabel="Aggregate completion tokens/second", xticks=[8, 16, 32], title="Varloop research checkpoint, 3 passes\nMedian and range of five interleaved rounds")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.15)
    for extension in ["png", "svg"]:
        fig.savefig(OUT / f"concurrency-sweep.{extension}", dpi=200)
    plt.close(fig)
    print("Saved measured pilot and concurrency charts as PNG and SVG.")


if __name__ == "__main__":
    main()
