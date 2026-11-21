#!/usr/bin/env python3
"""Plot measured text/cost and separately attributed publisher context."""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/publication/charts"
COLORS = {"math": "#205a9b", "humaneval": "#a04718", "gsm8k": "#00826e", "bbh": "#7a4e9b"}
NAMES = {"math": "MATH · 200", "humaneval": "HumanEval · 164", "gsm8k": "GSM8K · 150", "bbh": "BBH · 60, five tasks"}


def save(fig, name):
    fig.savefig(OUT / (name + ".png"), dpi=200, facecolor="white")
    fig.savefig(OUT / (name + ".svg"), facecolor="white")
    plt.close(fig)


def setup(title, subtitle):
    fig, ax = plt.subplots(figsize=(10.4, 6.4))
    fig.subplots_adjust(top=0.78, bottom=0.19, left=0.10, right=0.86)
    fig.text(0.10, 0.94, title, fontsize=18, weight="bold")
    fig.text(0.10, 0.89, "thinkingmachines/TML-d24-varloop-research · varloop research checkpoint", fontsize=11)
    fig.text(0.10, 0.84, subtitle, fontsize=10, color="#444444")
    ax.set_xlabel("Loop passes")
    ax.set_xticks(range(1, 7))
    ax.grid(alpha=0.18)
    ax.spines[["top", "right"]].set_visible(False)
    return fig, ax


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    a = json.loads((ROOT / "results/full/analysis.json").read_text())
    rows = [r for r in a["conditions"] if r["repeat"] == 0 and not r["share_cache"]]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    for name, title, subtitle, metric, ylabel in [("reasoning-tokens-vs-passes", "Written reasoning length versus loop passes", "Original runs · separate KV · temperature 0 · maximum concurrency 32", "mean_reasoning_tokens", "Mean visible reasoning tokens per problem"), ("cost-per-correct-vs-passes", "Inference cost per correct answer", "Measured batch wall time divided by correct count · excludes loading and grading", "gpu_seconds_per_correct", "GPU seconds per correct answer")]:
        fig, ax = setup(title, subtitle)
        for domain, color in COLORS.items():
            selected = sorted([r for r in rows if r["domain"] == domain], key=lambda r: r["passes"])
            ax.plot([r["passes"] for r in selected], [r[metric] for r in selected], "o-", color=color, label=NAMES[domain], linewidth=2)
        ax.set_ylabel(ylabel)
        ax.set_ylim(0, None)
        ax.axvspan(5.5, 6.2, color="#db8b32", alpha=0.07)
        ax.set_xlim(0.8, 6.2)
        ax.legend(fontsize=10, frameon=False)
        if metric == "gpu_seconds_per_correct":
            factor = 2.75 * 1000 / 3600
            right = ax.secondary_yaxis("right", functions=(lambda x: x * factor, lambda x: x / factor))
            right.set_ylabel("Estimated USD per 1,000 correct · $2.75/GPU-hour", fontsize=9)
            right.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:.2f}"))
        fig.text(0.10, 0.075, "1, 2, 4, 5: midtraining only · 3: post-training depth · 6: untrained, MATH only", fontsize=9, color="#444444")
        fig.text(0.10, 0.04, "Separate KV · original runs · temperature 0 · C32 · fixed subsets · batch-tail effects included.", fontsize=9, color="#444444")
        save(fig, name)

    card = json.loads((ROOT / "results/publication/model-card-context.json").read_text())
    series = next(r for r in card["publisher_scores"] if r["benchmark"] == "SimpleQA Verified")
    passes = [1, 3, 5]
    values = [series["publisher_percent_by_pass"][str(p)] for p in passes]
    knowledge_path = ROOT / "results/knowledge/analysis.json"
    knowledge = json.loads(knowledge_path.read_text()) if knowledge_path.exists() else None
    if knowledge:
        fig, ax = setup("SimpleQA Verified: measured knowledge control", "My 200 fixed questions · official GPT-4.1 grading · 95% Wilson intervals")
        observed = sorted(knowledge["conditions"], key=lambda r: r["passes"])
        y = [r["accuracy"] * 100 for r in observed]
        errors = [[r["accuracy"] * 100 - r["wilson_95"][0] * 100 for r in observed], [r["wilson_95"][1] * 100 - r["accuracy"] * 100 for r in observed]]
        ax.errorbar(passes, y, yerr=errors, fmt="o-", color="#205a9b", linewidth=2, capsize=5, label="Loop Dial · same 200 questions at each depth")
        for p, value in zip(passes, y):
            ax.annotate(f"{value:.1f}%", (p, value), xytext=(10, 8), textcoords="offset points", color="#205a9b")
    else:
        fig, ax = setup("SimpleQA Verified: publisher context only", "OUR KNOWLEDGE CONTROL WAS NOT RUN · no independent flatness result")
    ax.plot(passes, values, "--" if knowledge else "o--", color="#666666", linewidth=1.5, markersize=6, label="Publisher reference · different sample and protocol")
    if not knowledge:
        for p, value in zip(passes, values):
            ax.annotate(f"{value:.1f}%", (p, value), xytext=(0, 10), textcoords="offset points", ha="center")
    ymax = max(12, max(r["wilson_95"][1] * 100 for r in knowledge["conditions"]) + 3) if knowledge else 12
    ax.set(xticks=passes, xlim=(0.6, 5.4), ylim=(0, ymax), ylabel="Accuracy / publisher reference score (%)" if knowledge else "Published benchmark score (%)")
    ax.legend(loc="lower left", frameon=False, fontsize=10)
    note = "One run per depth · nonsignificance does not establish knowledge equivalence." if knowledge else "This is not Loop Dial control data. No confidence intervals or equivalence test are available here."
    fig.text(0.10, 0.10, note, fontsize=9, color="#9b3b22")
    fig.text(0.10, 0.06, "Source: thinkingmachines.ai/model-card/tml-d24-varloop-research/", fontsize=9, color="#444444")
    fig.text(0.10, 0.025, "Passes 1 and 5: midtraining only · 3: post-training depth. Fixed Inkling 2 Mini series excluded.", fontsize=9, color="#444444")
    save(fig, "knowledge-control-context")
    print(json.dumps({"figures": 3, "formats": ["png", "svg"], "new_inference": False, "knowledge_figure_source": "our measurements; publisher reference only" if knowledge else "publisher only"}))


if __name__ == "__main__":
    main()
