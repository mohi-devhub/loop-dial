# Loop Dial budget

Full study: **thinkingmachines/TML-d24-varloop-research varloop research checkpoint**. Authorized cap **$15**, in addition to the completed pilot. Opening HF credits: **$24.40**, user-reported. No inference after this study is authorized.

| Item | Measured / bounded cost |
| --- | --- |
| HF RTX PRO 6000, one job | ≤ $4.629133 |
| Modal CPU sandboxes including validation | ≤ $0.157861 |
| Full study combined | ≤ $4.786994 |

HF job: [withheld](https://huggingface.co/docs/hub/jobs). Submission 2026-11-21T05:10:49.214219+00:00; terminal status observed 2026-11-21T06:50:51.742361+00:00. Upper elapsed time 1.6674 GPU-hours. HF cost bound rounds elapsed submission-to-observation time up to whole minutes at $0.045833/minute. It includes provisioning, loading, warmup, inference, and shutdown observation; it is conservative relative to billable running time.

Modal is CPU-only. Each isolated sandbox requests a fixed 0.5 CPU and 1 GiB. Its bound counts local create-to-termination time at $0.094716/hour, approximately three times the checked resource rate. Preflight, self-tests, canonical-solution validation, generated candidates, failed attempts, and termination time are included. No other Modal project is touched. Modal project cap remains $2.

These are conservative resource-time estimates. HF billing API access was unavailable and no invoice has been read. A later user-reported final credit balance may establish the HF balance change, assuming no other HF usage; it does not verify Modal charges. Actual billed charges remain unverified.

The prelaunch [FORECAST.md](FORECAST.md) estimated $12.83 nominal, comprising $12.08 GPU plus a $0.75 CPU reserve. It retained all 4,734 scored generations because nominal cost was below $13. Its length assumptions were 3,072 tokens at three passes for MATH/BBH and 1,024 for code, anchored to measured pilot rates. The forecast and ordered budget cuts are saved in [forecast.json](results/full/forecast.json).

Observed three-pass mean completion lengths were 657 MATH tokens and 1485 BBH tokens, versus 3,072 assumed for each. HumanEval averaged 1252, versus 1,024 assumed. The MATH and BBH length assumptions were conservative, and measured finite-batch rates also differed from the pilot anchors. The full matrix completed without cuts.

Enforcement reserved cleanup cost: worker deadline 290 minutes, provider timeout 295, local cancellation at 300, and an additional 10-minute liability reserve. At the checked rate, 310 GPU minutes plus $0.75 CPU reserve is $14.95823. Sandbox admission also enforces the shared total after GPU termination. No automatic paid model retries are allowed.

The complete numerical ledger is [budget-report.json](results/full/budget-report.json). Raw job status history and sandbox resource-time entries are in results/full/job-state.json and results/full/modal-ledger.jsonl. Per-condition inference dollars/correct in REPORT.md exclude startup and grading; total bounds above include them.


<!-- publication-billing -->

## Publication billing check

The authenticated Jobs usage and credits APIs still return HTTP 403. Actual HF Jobs charges remain unverified. See [billing-access-check.json](results/full/billing-access-check.json). The separately approved SimpleQA control is complete under its $5 cap. See [its resource-cost calculation](results/knowledge/budget-report.json); the earlier $9 proposal is superseded. No further inference is authorized.

## Approved knowledge-control cost

The user approved a **$5 combined cap**, replacing the earlier $9 proposal. No further control runs are authorized.

| Component | USD | Basis |
| --- | --- | --- |
| HF GPU upper bound | 0.9167 | Submission through terminal observation, rounded up to a minute |
| Official grader usage cost upper bound | 0.8368 | Actual returned tokens at published Batch prices, before any caching discount |
| Combined resource-cost upper bound | 1.7535 | Under the approved $5 cap |

These are timestamp- and returned-usage-based resource estimates, not a verified invoice. The original study's HF billing-access limitation still applies. [Budget calculation](results/knowledge/budget-report.json) · [OpenAI Batch pricing](https://developers.openai.com/api/docs/guides/batch) · [approved protocol](KNOWLEDGE_PLAN.md)
