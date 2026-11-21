#!/usr/bin/env python3
"""Render the public README from the saved paired analysis."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    a = json.loads((ROOT / "results/full/analysis.json").read_text())
    k = json.loads((ROOT / "results/knowledge/analysis.json").read_text())
    b = json.loads((ROOT / "results/full/budget-report.json").read_text())
    kb = json.loads((ROOT / "results/knowledge/budget-report.json").read_text())
    rows = {(r["domain"], r["passes"]): r for r in a["conditions"] if not r["share_cache"] and r["repeat"] == 0}
    pair = next(p for p in a["paired_comparisons"] if p["domain"] == "math" and p["from_passes"] == 1 and p["to_passes"] == 3 and p["comparison"] == "separate")
    code = next(p for p in a["paired_comparisons"] if p["domain"] == "humaneval" and p["from_passes"] == 1 and p["to_passes"] == 3 and p["comparison"] == "separate")
    m3 = rows[("math", 3)]
    total = b["full_study_cost_upper_usd"] + kb["combined_resource_cost_upper_usd"]
    content = f'''# Loop Dial

What changes when you give a looped model more passes through the same layers?

We tested **thinkingmachines/TML-d24-varloop-research**, the varloop research checkpoint, not shipped Inkling 2 Mini. The [model card](https://thinkingmachines.ai/model-card/tml-d24-varloop-research/) describes a model whose loop count can change at inference. This study measures accuracy, written reasoning, latency, cache sharing and repeat variation on fixed subsets.

[Read the article](https://mohith.xyz/blog/loop-dial) · [Full report](REPORT.md) · [All result tables](FULL_RESULTS.md) · [Dataset licences](DATASETS.md)

## What we found

- On 200 MATH problems, accuracy rose from 92.5% at one pass to **99.0% at three**. The three-pass 95% Wilson interval is {m3['wilson_95'][0]*100:.1f}% to {m3['wilson_95'][1]*100:.1f}%. Four, five and six passes scored 97.5%, 97.5% and 98.0%. Paired tests did not demonstrate a gain beyond three.
- One to three passes reduced mean visible reasoning by **{-pair['reasoning_tokens']['relative_mean_change']*100:.1f}% on MATH** and **{-code['reasoning_tokens']['relative_mean_change']*100:.1f}% on HumanEval**. Among problems correct at both depths, the reductions were 27.8% and 20.4%.
- MATH batch GPU seconds per correct answer rose from **{m3['gpu_seconds_per_correct']:.3f} at three passes to {rows[('math',6)]['gpu_seconds_per_correct']:.3f} at six**. This nearly doubled inference cost on the same hardware. It excludes loading and grading.
- On 200 SimpleQA Verified questions, accuracy was **7.0%, 5.0% and 5.5%** at one, three and five passes. The one-versus-three exact McNemar p-value was **0.289**. Mean reasoning fell **34.5%**. This sample does not establish knowledge equivalence.

The measurements show shorter written reasoning. They do not reveal what the internal loops computed or establish a general depth limit.

## Results

![Accuracy by loop count](results/full/charts/accuracy-vs-passes.png)

![Written reasoning by loop count](results/publication/charts/reasoning-tokens-vs-passes.png)

![GPU time per correct answer](results/publication/charts/cost-per-correct-vs-passes.png)

![Our knowledge control with publisher reference](results/publication/charts/knowledge-control-context.png)

PNG and SVG versions are included. The knowledge chart uses our 95% Wilson intervals; the gray publisher curve is a reference only. The [model-card context tables](PUBLICATION_AUDIT.md) keep publisher results separate from ours.

## Setup

The full matrix has 4,734 scored responses: GSM8K 150 problems at passes 1–5; MATH-500 200 problems, 40 per level, at passes 1–6; HumanEval 164 at passes 1–5; and 60 BBH problems across five tasks at passes 1, 3 and 5. Shared KV cache was tested at passes 3 and 5 on MATH and HumanEval. Two extra runs at passes 1 and 3 used 100 matched MATH problems and all HumanEval tasks.

The separately approved SimpleQA control adds 600 scored responses on the same 200 questions at passes 1, 3 and 5. All runs used temperature zero and maximum concurrency 32. The SGLang Inkling reasoning parser separated visible reasoning from final answers. Math uses numeric equivalence; HumanEval uses sandboxed execution; SimpleQA uses the official rubric and GPT-4.1 snapshot. Saved grades are included.

## Reproduce without a GPU

Use Python 3.13 and the pinned analysis dependencies:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-analysis.txt
.venv/bin/python scripts/reproduce.py
```

After dependency installation, reproduction disables network access. It reads the saved scored results, regenerates the analyses, result tables, report, README and charts, and compares all numerical analysis values against the archived reference. No model weights, GPU, API key or paid judge is needed. It does not rerun sandbox execution or LLM grading. See [REPRODUCE.md](REPRODUCE.md) for the distinction.

The complete reasoning and answer text, scores, token counts, request timings and generated-token usage are in compressed JSONL files under [results/full](results/full) and [results/knowledge](results/knowledge). Per-chunk timestamp arrays were reduced to their first/last times and count. Every reported timing scalar is preserved. Raw server logs, job-account identifiers, credentials and workstation paths are excluded.

The [dataset manifest](data/full/manifest.json) and [knowledge manifest](data/knowledge/manifest.json) publish subset IDs and source revisions. [scripts/fetch_datasets.py](scripts/fetch_datasets.py) fetches original sources and verifies their hashes. The inference code is included for inspection and future experiments with your own credentials and budget. Archived configurations cannot launch paid jobs by default.

## Cost and limits

The original full-study resource upper bound was **${b['full_study_cost_upper_usd']:.2f}**. The knowledge control added **${kb['combined_resource_cost_upper_usd']:.2f}**. Together this is approximately **${total:.2f}**, before any billing discounts and excluding the earlier pilot. These are timestamp- and returned-token-based estimates, **not verified invoices**. [BUDGET.md](BUDGET.md) records the components and caps.

The checkpoint was exposed to passes 1–5 in later midtraining, sampled in the ratio **1:2:6:2:1**, and post-trained at **three passes**. Passes 1, 2, 4 and 5 are midtraining only; six is beyond the trained range. The [model card](https://thinkingmachines.ai/model-card/tml-d24-varloop-research/) is the source for those labels.

MATH is near saturation in this subset. Level 5 scored 38/40 at three passes, or 95.0%, with a wide 95% CI of 83.5% to 98.6%. Recovering both remaining errors would add only one point overall. Fixed benchmark familiarity, an 8,192-token output cap, one GPU/runtime, three repeats in selected cells and one run per knowledge depth limit generalization. Nonsignificance does not establish equivalence. Compute-matched observations are not controlled token-budget experiments.

## Licence and sources

Study code is MIT. Third-party dataset text retains its upstream licence and attribution. See [LICENSE](LICENSE), [DATASETS.md](DATASETS.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Model weights are not redistributed.

Sources: [research model card](https://thinkingmachines.ai/model-card/tml-d24-varloop-research/), [Thinking Machines release post](https://thinkingmachines.ai/news/inkling-2-mini/), and [SGLang cookbook](https://docs.sglang.io/cookbook/autoregressive/ThinkingMachines/Inkling-2-Mini). The cookbook reports GSM8K 84.0% at one pass, 88.5% at three and 90.0% at three with shared cache. Its figures use a different, incompletely pinned protocol and are not merged with our measurements.
'''
    (ROOT / "README.md").write_text(content)


if __name__ == "__main__":
    main()
