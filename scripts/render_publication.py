#!/usr/bin/env python3
"""Render the publication completeness audit without launching inference."""

import json
from pathlib import Path
import re

from render_full_report import f, interval, pct, pvalue, table


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/publication"
CARD = "https://thinkingmachines.ai/model-card/tml-d24-varloop-research/"
NAMES = {"math": "MATH", "gsm8k": "GSM8K", "humaneval": "HumanEval", "bbh": "BBH, five tasks"}


def result_table(rows):
    return table(["Domain or level", "Passes", "Cache", "Run", "Correct / n", "Accuracy, 95% Wilson CI (%)", "Mean / median reasoning tokens", "Request s / correct", "Batch GPU s / correct"], [[NAMES[r["domain"]] + (f" level {r['math_level']}" if r["math_level"] is not None else " overall"), r["passes"], r["cache"], r["repeat"], f"{r['correct']}/{r['n_scored']}", pct(r["accuracy"]) + " " + interval(r["wilson_95"], 100), f(r["mean_reasoning_tokens"]) + " / " + f(r["median_reasoning_tokens"]), f(r["request_seconds_per_correct"], 3), f(r["gpu_seconds_per_correct"], 3)] for r in rows])


def main():
    a = json.loads((OUT / "analysis.json").read_text())
    original = json.loads((ROOT / "results/full/analysis.json").read_text())
    card = json.loads((OUT / "model-card-context.json").read_text())
    forecast = json.loads((OUT / "knowledge-control-forecast.json").read_text())
    billing = json.loads((ROOT / "results/full/billing-access-check.json").read_text())
    knowledge_path = ROOT / "results/knowledge/analysis.json"
    knowledge = json.loads(knowledge_path.read_text()) if knowledge_path.exists() else None
    if knowledge:
        NAMES["simpleqa"] = "SimpleQA Verified"
    results = sorted(a["full_results"], key=lambda r: (list(NAMES).index(r["domain"]), r["passes"], r["math_level"] or 0, r["cache"], r["repeat"]))
    a["level5_ceiling"] = sorted(a["level5_ceiling"], key=lambda r: r["passes"])
    timing_note = "Request s/correct is the sum of measured request latencies, including failed answers, divided by the number correct. Requests overlap at concurrency 32, so this is not billed GPU wall time. Batch GPU s/correct uses the measured whole-domain batch duration. Level-only GPU times are unavailable because the levels ran together; the dash means unmeasured, not zero. No GPU time is allocated to levels by token count."
    full = ["# Full saved-results table", "", "Checkpoint: **thinkingmachines/TML-d24-varloop-research, varloop research checkpoint**.", "", "The 91 rows cover all 31 domain/cache/repeat cells plus their 60 MATH level cells. They reuse the 4,734 saved responses. Level rows are subdivisions, not extra generations.", "", "Reasoning lengths count separately retokenized visible reasoning text. API usage counts, including channel markers, are retained separately in the CSV. Accuracy uses numeric equivalence for math and sandboxed pass@1 for HumanEval; literal math matching remains secondary.", "", timing_note, "", "Main runs used GSM8K passes 1–5, MATH 1–6, HumanEval 1–5, and BBH 1/3/5. Other pass/domain combinations were not run under the approved matrix.", "", "Training labels: passes 1, 2, 4, 5 are midtraining only; 3 is the post-training depth; 6 is untrained. The [model card](" + CARD + ") gives later-midtraining sampling 1:2:6:2:1 and post-training at 3.", ""]
    for run, cache, name in [(0, "separate", "Main, separate KV"), (0, "shared", "Shared KV"), (1, "separate", "Extra repeat 1"), (2, "separate", "Extra repeat 2")]:
        selected = sorted([r for r in results if r["repeat"] == run and r["cache"] == cache], key=lambda r: (list(NAMES).index(r["domain"]), r["passes"], r["math_level"] or 0))
        full += ["## " + name, "", result_table(selected), ""]
    full += ["The [CSV](results/publication/full-results.csv) retains training labels, API reasoning counts, answer lengths, truncations, and the other metrics. The [JSON](results/publication/analysis.json) also contains paired tests and bootstrap results.", ""]
    (ROOT / "FULL_RESULTS.md").write_text("\n".join(full))
    if knowledge:
        path = ROOT / "FULL_RESULTS.md"
        path.write_text(path.read_text().replace("91 rows cover all 31 domain/cache/repeat cells", "94 rows cover all 34 domain/cache/repeat cells").replace("4,734 saved responses", "5,334 saved responses, including the 600-response knowledge control"))

    status_rows = [[1, "Added", "Full results and timing definitions: FULL_RESULTS.md; per-level GPU isolation was not measured."], [2, "Covered and expanded", "Per-level paired length changes and hard/easy interaction below."], [3, "Expanded", "Per-run 1 vs 3 paired tests and hierarchical paired CIs below."], [4, "Covered and expanded", "Shared/separate KV at 3 and 5, with CIs and per-correct time."], [5, "Not run", "SimpleQA Verified is absent from the frozen matrix and saved responses. New-run forecast below."], [6, "Added", "Publisher context is separate; training ratio and depth labels cite the model card."], [7, "Added", "Level 5 scored 38/40 at three passes. Ceiling and headroom note below."], [8, "Not verified", "HF billing endpoints return 403. Cost estimates remain separate from an actual bill."]]
    lines = ["# Publication audit and additions", "", "Checkpoint: **thinkingmachines/TML-d24-varloop-research, varloop research checkpoint**. This audit uses saved outputs and public reference material. No new inference or paid grading was launched.", "", table(["Item", "Status", "Evidence or limitation"], status_rows), "", "## Full results and level timing", "", "[FULL_RESULTS.md](FULL_RESULTS.md) and [full-results.csv](results/publication/full-results.csv) provide accuracy with 95% CIs, reasoning lengths, and time per correct answer for every completed setting and MATH level.", "", timing_note, "", "The primary per-level MATH rows are:", "", result_table([r for r in results if r["domain"] == "math" and r["math_level"] is not None and r["repeat"] == 0 and r["cache"] == "separate"]), "", "## Reasoning reduction by MATH level", "", "Paired change from one to three passes. Negative values mean fewer visible reasoning tokens. Each row contains the same 40 problems at both depths; intervals are paired bootstrap intervals.", ""]
    level_pairs = [r for r in a["math_level_comparisons"] if r["to_passes"] == 3]
    lines += [table(["Level", "Paired n", "Mean token change, 95% CI", "Relative change, 95% CI (%)"], [[r["level"], r["n"], f(r["reasoning_tokens"]["mean_difference"]) + " " + interval(r["reasoning_tokens"]["difference_95"]), pct(r["reasoning_tokens"]["relative_mean_change"]) + " " + interval(r["reasoning_tokens"]["relative_change_95"], 100)] for r in level_pairs]), "", "Hard levels 4–5 saved more raw tokens than easy levels 1–2, but began with longer responses. The hard-minus-easy relative change is +4.1 percentage points, with a 95% CI of −34.0 to +29.4. These data do not resolve stronger proportional shortening on hard problems. Paired comparisons against one pass at every other depth are retained in the publication JSON; those additional comparisons are exploratory.", "", "## Repeat-run CIs and paired tests at one versus three passes", "", "The main report already contains each setting's three-run accuracy interval. The tables here add paired depth comparisons within each run and uncertainty in mean reasoning length. The MATH comparison uses the same 100 problems across all six depth/run cells. HumanEval uses the same 164.", ""]
    paired_rows = []
    pooled_rows = []
    for domain in a["repeat_paired_comparisons"]:
        for r in domain["per_run"]:
            paired_rows.append([NAMES[domain["domain"]], r["repeat"], r["n"], f(r["accuracy_difference"] * 100), f"{r['mcnemar']['gains']} / {r['mcnemar']['losses']}", pvalue(r["mcnemar"]["exact_two_sided_p"]), f(r["reasoning_tokens"]["mean_difference"]) + " " + interval(r["reasoning_tokens"]["difference_95"])])
        h = domain["hierarchical_paired_effects"]
        pooled_rows.append([NAMES[domain["domain"]], domain["paired_problem_count"], f(h["correct"]["mean_difference"] * 100) + " " + interval(h["correct"]["hierarchical_paired_95"], 100), f(h["reasoning_tokens"]["mean_difference"]) + " " + interval(h["reasoning_tokens"]["hierarchical_paired_95"])])
    lines += [table(["Domain", "Run", "Paired n", "Accuracy change pp", "Gains / losses", "Exact McNemar p", "Mean token change, paired 95% CI"], paired_rows), "", table(["Domain", "Distinct paired tasks", "Mean accuracy change pp, hierarchical 95% CI", "Mean token change, hierarchical paired 95% CI"], pooled_rows), "", "The hierarchical calculation resamples both runs and problems. It does not pool repeated tasks into a larger independent sample. McNemar tests are per run; these extra repeat comparisons are exploratory. MATH run 0 was generated in a 200-problem batch, so its matched 100 examples differ in batch composition from the repeat batches.", "", table(["Domain", "Passes", "Distinct tasks", "Run mean reasoning tokens", "Overall mean, hierarchical 95% CI"], [[NAMES[r["domain"]], r["passes"], r["paired_n"], ", ".join(f(v) for v in r["per_run_mean_reasoning_tokens"]), f(r["mean_reasoning_tokens"]) + " " + interval(r["hierarchical_reasoning_mean_95"])] for r in a["repeat_reasoning_cis"]]), "", "## Shared versus separate KV cache", ""]
    conditions = {(r["domain"], r["passes"], r["cache"], r["repeat"]): r for r in results if r["math_level"] is None}
    cache_rows = []
    for pair in original["paired_comparisons"]:
        if pair["comparison"] != "shared_vs_separate":
            continue
        domain, p = pair["domain"], pair["from_passes"]
        low, high = [conditions[(domain, p, cache, 0)] for cache in ["separate", "shared"]]
        cache_rows.append([NAMES[domain], p, pct(low["accuracy"]) + " " + interval(low["wilson_95"], 100), pct(high["accuracy"]) + " " + interval(high["wilson_95"], 100), pvalue(pair["mcnemar"]["exact_two_sided_p"]), f(pair["reasoning_tokens"]["mean_difference"]) + " " + interval(pair["reasoning_tokens"]["difference_95"]), f(low["gpu_seconds_per_correct"], 3) + " / " + f(high["gpu_seconds_per_correct"], 3)])
    lines += [table(["Domain", "Passes", "Separate accuracy, 95% CI (%)", "Shared accuracy, 95% CI (%)", "Paired McNemar p", "Shared minus separate reasoning, 95% CI", "GPU s/correct, separate / shared"], cache_rows), "", "Cache comparisons use the same tasks. They show no measured aggregate accuracy gain for shared KV in these cells. Timing can change with the generated responses as well as the cache implementation.", "", "## SimpleQA Verified control: missing from this study", "", "No SimpleQA Verified responses were generated at passes 1, 3, or 5. Its absence is recorded as null, never as zero accuracy. Our study therefore cannot say whether knowledge stayed flat. No additional compute has been launched.", "", table(["Passes", "Our SimpleQA control", "Publisher's SimpleQA score (%)"], [[p, "Not run", card_score(card, "SimpleQA Verified", p)] for p in [1, 3, 5]]), "", "The small variation in the publisher's point estimates is context, not a replicated control or a test of equivalence. We do not have the publisher's per-question outputs or confidence intervals. The third publication chart is marked **publisher data only; our control not run**.", "", "![Publisher knowledge context only](results/publication/charts/knowledge-control-context.png)", "", "## Model-card context and training exposure", "", "Later midtraining sampled passes 1–5 in the ratio **1:2:6:2:1**, followed by post-training at **3 passes**. Passes 1, 2, 4, and 5 are labeled **midtraining only**; pass 3 is the post-training depth; pass 6 is **untrained**. [Thinking Machines model card, training section](" + CARD + ")", "", "Our measurements:", ""]
    own_rows = []
    for domain in NAMES:
        cells = [conditions.get((domain, p, "separate", 0)) for p in range(1, 7)]
        own_rows.append([NAMES[domain], *[pct(r["accuracy"]) if r else "Not run" for r in cells]])
    lines += [table(["Loop Dial subset accuracy (%)", "1 pass", "2 passes", "3 passes", "4 passes", "5 passes", "6 passes"], own_rows), "", "Published measurements on different benchmarks:", "", table(["Publisher benchmark, score (%)", "1 pass", "2 passes", "3 passes", "4 passes", "5 passes"], [[r["benchmark"], *[f(r["publisher_percent_by_pass"][str(p)]) for p in range(1, 6)]] for r in card["publisher_scores"]]), "", "Source: [thinkingmachines/TML-d24-varloop-research model card](" + CARD + "). The two tables are not combined, averaged, or treated as matched evaluations. The card does not report our GSM8K, MATH-500 subset, HumanEval, or five-task BBH protocol. Its separate fixed Inkling 2 Mini series is excluded from this table. The SGLang cookbook sanity comparison remains a separate reference in the main report.", "", "## Ceiling and level-5 headroom", ""]
    lines += [table(["Passes", "Level-5 correct / n", "Accuracy, 95% Wilson CI (%)"], [[r["passes"], f"{r['correct']}/{r['n_scored']}", pct(r["accuracy"]) + " " + interval(r["wilson_95"], 100)] for r in a["level5_ceiling"]]), "", "At three passes, levels 1–4 each scored 40/40; level 5 scored **38/40, or 95.0% (95% Wilson CI 83.5%–98.6%)**. Level 5 has observed benchmark headroom, but only two failures on 40 questions. Recovering both would add at most one percentage point to this 200-question overall score. The interval is broad, so the study cannot precisely locate a capability ceiling or establish that more depth would recover those failures.", "", "## Actual HF Jobs bill: access still unavailable", "", "The authenticated Jobs-usage, usage-v2, and credits endpoints return **HTTP 403** on the publication recheck. The existing Superset browser launcher points to a missing desktop app, and a plain HTTP page fetch is not an authenticated billing receipt. No invoice or exact Jobs charge has been verified. [Access-check record](results/full/billing-access-check.json)", "", "The HF timestamp-based upper bound remains **$4.629133**, and the combined HF plus Modal upper bound remains **$4.786994**. These are estimates, not the actual bill. The starting HF credit balance is user-reported at $24.40; no closing balance has been supplied.", "", "## Cost before any missing-control run", "", "The following are proposals only. The 200-question subset at passes 1/3/5 is the recommended size for the remaining budget. All generation settings and grading rules would be frozen before execution. A small sample can still fail to resolve modest knowledge differences.", "", table(["Questions", "New generations", "GPU nominal USD", "Semantic grading nominal USD", "Total nominal USD", "Fits remaining original budget nominally"], [[r["questions"], r["generations"], f(r["gpu_nominal_usd"], 2), f(r["semantic_grader_nominal_usd"], 2), f(r["total_nominal_usd"], 2), "Yes" if r["total_nominal_usd"] <= forecast["remaining_under_original_15_usd_cap"] else "No"] for r in forecast["options"]]), "", f"Proposed 200-question incremental hard cap: **$9**. Combined with the completed study's bound, the maximum allocation is **${forecast['combined_upper_budget_if_cap_approved_usd']:.2f}**, below $15. The nominal estimate is **$2.94**. This cap has not been approved and no job has been started.", "", "The estimate assumes 1,024 output tokens per question, aggregate rates of 1,300/600/400 tokens per second at passes 1/3/5, and nine minutes of startup. These are conservative anchors from other domains, not SimpleQA measurements. If every response used the entire 8,192-token allowance, the estimated GPU cost would be $6.60 before grading. A watchdog must enforce the approved cap if actual throughput is lower.", "", "The semantic-grader allowance uses 1,200 input tokens and 64 output tokens per judgment at the published GPT-4.1 price of $2/$8 per million tokens. That model is deprecated, so access and availability must be checked before any run. No grader credential was read or API call made. A replacement or blinded manual review requires an agreed protocol; the math numeric grader is unsuitable for factual names and aliases. Grader charges use separate API billing, not HF credits. [Dataset and grading description](https://huggingface.co/datasets/google/simpleqa-verified) · [Grader price and deprecation status](https://developers.openai.com/api/docs/models/gpt-4.1) · [Exact forecast](results/publication/knowledge-control-forecast.json)", ""]
    if knowledge:
        from render_knowledge import knowledge_sections, replace_section
        summary, cost = knowledge_sections(knowledge)
        lines = replace_section(lines, "## SimpleQA Verified control: missing from this study", summary)
        lines = replace_section(lines, "## Cost before any missing-control run", cost)
        lines = [line.replace("This audit uses saved outputs and public reference material. No new inference or paid grading was launched.", "This audit includes the subsequently approved 600-response SimpleQA control with official grading. Its incremental cap was $5.").replace("| 5 | Not run | SimpleQA Verified is absent from the frozen matrix and saved responses. New-run forecast below. |", "| 5 | Complete | 200 fixed questions at passes 1/3/5, official grading, CIs and paired tests below. |") .replace("Published measurements on different benchmarks:", "Publisher measurements, reported separately:") for line in lines]
    (ROOT / "PUBLICATION_AUDIT.md").write_text("\n".join(lines))
    report = (ROOT / "REPORT.md").read_text()
    marker = "\n\n<!-- publication-audit -->"
    report = report.split(marker, 1)[0]
    report = re.sub(r"\n\n<!-- publication-notice -->.*?<!-- /publication-notice -->", "", report, flags=re.S)
    report = re.sub(r"<!-- knowledge-finding -->.*?<!-- /knowledge-finding -->\n\n", "", report, flags=re.S)
    report = re.sub(r"(?m)^Complete:", "Approved matrix complete:", report)
    header_end = report.find("\n\n", report.find("**Checkpoint:"))
    notice = "\n\n<!-- publication-notice -->\n**Publication gaps:** SimpleQA Verified was not run. The actual HF Jobs bill remains unverified because billing access returns 403. [Completeness audit and additions](PUBLICATION_AUDIT.md) include a proposed control budget. No new compute was launched.\n<!-- /publication-notice -->"
    if knowledge:
        notice = "\n\n<!-- publication-notice -->\n**Knowledge control complete:** 600 SimpleQA Verified outputs on 200 fixed questions at passes 1/3/5 were graded with the official rubric and GPT-4.1 snapshot under the approved $5 cap. [Control results](KNOWLEDGE_REPORT.md). The actual HF bill remains unverified because billing access returns 403.\n<!-- /publication-notice -->"
        report = report.replace("No follow-up model inference is authorized or launched.", "The separately approved 600-response SimpleQA control is reported below. No further inference is authorized.")
        report = report.replace("No controlled token-budget sweep or extra post-study generations were run.", "No controlled token-budget sweep was run. The separate approved SimpleQA control is reported below.")
        points = "; ".join(f"{r['passes']} {'pass' if r['passes'] == 1 else 'passes'}: {pct(r['accuracy'])} (95% CI {interval(r['wilson_95'], 100)})" for r in knowledge["conditions"])
        pair = knowledge["paired_comparisons"][0]
        finding = "<!-- knowledge-finding -->\n**Knowledge control:** On the same 200 SimpleQA Verified questions, official grading gave " + points + ". The paired one-to-three-pass accuracy change was " + f(pair["accuracy_difference"] * 100) + " percentage points (95% CI " + interval(pair["accuracy_difference_95"], 100) + "), exact McNemar p = " + pvalue(pair["mcnemar"]["exact_two_sided_p"]) + ". No equivalence margin was specified; these data do not establish that knowledge stays flat. [Full control results](KNOWLEDGE_REPORT.md).\n<!-- /knowledge-finding -->\n\n"
        report = report.replace("## Findings\n\n", "## Findings\n\n" + finding, 1)
        report = report.replace("Most of the measured benefit arrived", "On the original math, code and reasoning subsets, most of the measured benefit arrived", 1)
    report = report[:header_end] + notice + report[header_end:]
    appendix = "\n".join(lines).replace("# Publication audit and additions", "## Publication audit and additions", 1)
    appendix = appendix.replace("\n## ", "\n### ")
    appendix = appendix.replace("### Publication audit and additions", "## Publication audit and additions", 1)
    (ROOT / "REPORT.md").write_text(report.rstrip() + marker + "\n\n" + appendix + "\n")
    budget = (ROOT / "BUDGET.md").read_text().split("\n\n<!-- publication-billing -->", 1)[0]
    budget += "\n\n<!-- publication-billing -->\n\n## Publication billing check\n\nThe authenticated Jobs usage and credits APIs still return HTTP 403. Actual HF Jobs charges remain unverified. See [billing-access-check.json](results/full/billing-access-check.json). The SimpleQA control was not run. Its [forecast](results/publication/knowledge-control-forecast.json) is a proposal with no new spend authorization.\n"
    if knowledge:
        budget = budget.replace("The SimpleQA control was not run. Its [forecast](results/publication/knowledge-control-forecast.json) is a proposal with no new spend authorization.", "The separately approved SimpleQA control is complete under its $5 cap. See [its resource-cost calculation](results/knowledge/budget-report.json); the earlier $9 proposal is superseded. No further inference is authorized.")
        budget += "\n" + "\n".join(cost)
    (ROOT / "BUDGET.md").write_text(budget)
    (OUT / "coverage.json").write_text(json.dumps({"items": status_rows, "new_compute_launched": False, "knowledge_control_complete": False, "actual_bill_verified": billing["invoice_verified"]}, indent=2) + "\n")
    if knowledge:
        status_rows[4] = [5, "Complete", "Officially graded 200-question knowledge control at passes 1/3/5"]
        (OUT / "coverage.json").write_text(json.dumps({"items": status_rows, "new_compute_launched": True, "new_compute_scope": "User-approved knowledge control, $5 cap", "knowledge_control_complete": True, "actual_bill_verified": billing["invoice_verified"]}, indent=2) + "\n")
    print(json.dumps({"full_table_rows": len(results), "report_updated": True, "knowledge_control_run": knowledge is not None, "actual_bill_verified": False}))


def card_score(card, name, passes):
    return next(r["publisher_percent_by_pass"][str(passes)] for r in card["publisher_scores"] if r["benchmark"] == name)


if __name__ == "__main__":
    main()
