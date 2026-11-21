# Approved full-study forecast

This forecast was computed before full-study GPU inference. The approved checkpoint is `thinkingmachines/TML-d24-varloop-research`, revision `657b53ba5da7baefe9ff15dca5cd25f5bd3dbaa2`. The full-study hard cap is **$15**, separate from the completed approximately $0.60 pilot. Starting HF credits reported by the user are $24.40.

The requested matrix costs **$12.83 nominal**, including $12.08 GPU time and a $0.75 code-sandbox reserve. The nominal amount excludes unused contingency inside the $15 cap. Because it is below $13, neither authorized cut is applied. If the initial forecast had exceeded $13, the script would first drop hard reasoning and then reduce GSM8K to 100.

| Work | Outputs |
| --- | ---: |
| GSM8K 150, passes 1–5 | 750 |
| MATH 200, passes 1–6 | 1,200 |
| HumanEval 164, passes 1–5 | 820 |
| Hard reasoning 60, passes 1/3/5 | 180 |
| Shared KV 3/5 on MATH and HumanEval | 728 |
| Two extra repeats at 1/3 on MATH 100 and HumanEval 164 | 1,056 |
| Scored total | **4,734** |

The hard set is public BIG-Bench-Hard, with 12 fixed examples from each of five named tasks. GPQA file access is unavailable with the Jobs-only token. MATH uses 40 questions per level and the repeat subset uses 20 per level. Seeds, dataset revisions, IDs, and prompt hashes are frozen in [data/full/manifest.json](data/full/manifest.json).

GPU time is forecast at **4.39 hours**, including **0.41 hours** for 12 cold server starts and warmup. Measured pilot rates at passes 1, 3, and 6 anchor the estimate; intermediate seconds per token are interpolated. Only GSM8K output lengths are measured. Pass-3 mean output assumptions are 3,072 tokens for MATH, 1,024 for code, and 3,072 for hard reasoning. Their relative length changes are assumed to follow GSM8K. Shared KV receives no assumed speedup.

A 25% increase in decode time would cost **$15.57**, so completion is not guaranteed at the cap. The worker, provider, and independent local watchdog stop the job early enough to reserve shutdown liability. At the checked $0.045833/minute rate, the watchdog plus cleanup reserve and $0.75 CPU reserve bound planned liability at **$14.95823**. All failed starts and sandbox costs count toward the same $15.

No unlisted inference controls or post-study follow-up runs are included. Any compute-matched analysis must use the authorized observations and must be labeled observational. The exact forecast and ordered-cut logic are reproducible with `python3 scripts/forecast_full.py` and saved in [results/full/forecast.json](results/full/forecast.json).
