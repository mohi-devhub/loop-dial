#!/usr/bin/env python3
"""Render the completed control; never invent an unmeasured result."""

import json
from pathlib import Path

from render_full_report import f, interval, pct, pvalue, table


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/knowledge"


def knowledge_sections(analysis):
    budget = json.loads((OUT / "budget-report.json").read_text())
    manifest = json.loads((ROOT / "data/knowledge/manifest.json").read_text())
    comparison = analysis["paired_comparisons"][0]
    assert comparison["from_passes"] == 1 and comparison["to_passes"] == 3 and comparison["n_accuracy_pairs"] == 200
    scores = table(["Passes", "Correct / n", "Accuracy, 95% Wilson CI (%)", "Mean reasoning, bootstrap 95% CI", "Median reasoning", "Mean answer tokens", "Incorrect / not attempted"], [[r["passes"], f"{r['correct']}/200", pct(r["accuracy"]) + " " + interval(r["wilson_95"], 100), f(r["mean_reasoning_tokens"]) + " " + interval(r["reasoning_mean_95"]), f(r["median_reasoning_tokens"]), f(r["mean_answer_tokens"]), f"{r['grade_counts'].get('INCORRECT', 0)} / {r['grade_counts'].get('NOT_ATTEMPTED', 0)}"] for r in analysis["conditions"]])
    pair = table(["Paired comparison", "Accuracy change pp, 95% CI", "Gains / losses", "Exact McNemar p", "Reasoning-token change, paired 95% CI"], [["1 → 3 passes, n=200", f(comparison["accuracy_difference"] * 100) + " " + interval(comparison["accuracy_difference_95"], 100), f"{comparison['mcnemar']['gains']} / {comparison['mcnemar']['losses']}", pvalue(comparison["mcnemar"]["exact_two_sided_p"]), f(comparison["reasoning_tokens"]["mean_difference"]) + " " + interval(comparison["reasoning_tokens"]["difference_95"])]])
    p = comparison["mcnemar"]["exact_two_sided_p"]
    verdict = "The paired test did not resolve an accuracy difference between one and three passes." if p >= 0.05 else "The paired test detected an accuracy difference between one and three passes on this subset."
    verdict += " The intervals describe sampling uncertainty and do not include automated-grader error."
    summary = ["## SimpleQA Verified: our measured knowledge control", "", "Checkpoint: **thinkingmachines/TML-d24-varloop-research, varloop research checkpoint**. The separately approved control contains **600 graded responses on the same 200 questions** at passes 1, 3 and 5.", "", scores, "", pair, "", verdict + " A nonsignificant test does not prove equivalence, and no equivalence margin was specified. A 200-question subset and one run per depth cannot establish that knowledge stays flat in general. All three depth estimates and their intervals are shown rather than reduced to a flat/non-flat label.", "", "The subset was frozen by hash ranking with seed 20261121 before generation. Prompts were the bare questions, with no tools or retrieval, temperature zero, seed 1729, concurrency 32, separate KV caches, context 16,384 and output cap 8,192. Reasoning length is visible reasoning retokenized with the checkpoint tokenizer. API counts and complete raw traces are retained. Accuracy includes incorrect answers and non-attempts in its denominator.", "", "Grading uses the exact official SimpleQA Verified rubric and **gpt-4.1-2025-04-14**, via OpenAI Batch with judge temperature zero and a 16-token A/B/C response allowance. Only the final answer channel is sent to the judge. Identical complete judge prompts share a judgment; malformed judgments stop scoring rather than being silently counted. These execution settings are documented alongside the official source.", "", f"All {budget['grading_requests_completed']} distinct official grading requests completed; {budget['reused_identical_prompt_judgments']} identical prompts reused a judgment. There were no inference errors. Truncations by pass are " + ", ".join(f"{r['passes']}: {r['truncations']}" for r in analysis["conditions"]) + ".", "", "The chart shows **our estimates with 95% Wilson intervals**. The gray dashed publisher curve is a reference only: its sample and protocol are not matched to our 200-question control. No publisher results are pooled into our accuracy, intervals or tests.", "", "![Measured SimpleQA Verified control and publisher reference](results/publication/charts/knowledge-control-context.png)", "", "Sources: [official dataset and methodology](https://huggingface.co/datasets/google/simpleqa-verified), [official grader notebook](https://www.kaggle.com/code/nanliao7/simpleqa-verified-benchmark-starter-code), [model-card reference](https://thinkingmachines.ai/model-card/tml-d24-varloop-research/). [Subset and source manifest](data/knowledge/manifest.json) · [complete analysis](results/knowledge/analysis.json) · [raw official judgments](results/knowledge/grader-output.jsonl) · [run configuration](knowledge-config.json)", ""]
    cost = ["## Approved knowledge-control cost", "", "The user approved a **$5 combined cap**, replacing the earlier $9 proposal. No further control runs are authorized.", "", table(["Component", "USD", "Basis"], [["HF GPU upper bound", f(budget["gpu_timestamp_upper_usd"], 4), "Submission through terminal observation, rounded up to a minute"], ["Official grader usage cost upper bound", f(budget["grader_usage_cost_upper_usd"], 4), "Actual returned tokens at published Batch prices, before any caching discount"], ["Combined resource-cost upper bound", f(budget["combined_resource_cost_upper_usd"], 4), "Under the approved $5 cap"]]), "", "These are timestamp- and returned-usage-based resource estimates, not a verified invoice. The original study's HF billing-access limitation still applies. [Budget calculation](results/knowledge/budget-report.json) · [OpenAI Batch pricing](https://developers.openai.com/api/docs/guides/batch) · [approved protocol](KNOWLEDGE_PLAN.md)", ""]
    assert manifest["question_count"] == 200
    uncapped = comparison["reasoning_sensitivity"]["neither_truncated"]
    sensitivity = "Reasoning-length sensitivity: among the " + str(uncapped["n"]) + " questions uncapped at both one and three passes, mean reasoning changed by " + f(uncapped["mean_difference"]) + " tokens (paired 95% CI " + interval(uncapped["difference_95"]) + "), or " + pct(uncapped["relative_mean_change"]) + ". This descriptive subset excludes capped outputs; it is not a controlled token-budget experiment."
    summary += [sensitivity, ""]
    return summary, cost


def replace_section(lines, heading, replacement):
    start = lines.index(heading)
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[:start] + replacement + lines[end:]


def main():
    analysis = json.loads((OUT / "analysis.json").read_text())
    summary, cost = knowledge_sections(analysis)
    (ROOT / "KNOWLEDGE_REPORT.md").write_text("\n".join(["# SimpleQA Verified control", "", *summary[2:], *cost]))
    print(json.dumps({"report": "KNOWLEDGE_REPORT.md", "scored_outputs": analysis["scored_outputs"]}))


if __name__ == "__main__":
    main()
