# Full saved-results table

Checkpoint: **thinkingmachines/TML-d24-varloop-research, varloop research checkpoint**.

The 94 rows cover all 34 domain/cache/repeat cells plus their 60 MATH level cells. They reuse the 5,334 saved responses, including the 600-response knowledge control. Level rows are subdivisions, not extra generations.

Reasoning lengths count separately retokenized visible reasoning text. API usage counts, including channel markers, are retained separately in the CSV. Accuracy uses numeric equivalence for math and sandboxed pass@1 for HumanEval; literal math matching remains secondary.

Request s/correct is the sum of measured request latencies, including failed answers, divided by the number correct. Requests overlap at concurrency 32, so this is not billed GPU wall time. Batch GPU s/correct uses the measured whole-domain batch duration. Level-only GPU times are unavailable because the levels ran together; the dash means unmeasured, not zero. No GPU time is allocated to levels by token count.

Main runs used GSM8K passes 1–5, MATH 1–6, HumanEval 1–5, and BBH 1/3/5. Other pass/domain combinations were not run under the approved matrix.

Training labels: passes 1, 2, 4, 5 are midtraining only; 3 is the post-training depth; 6 is untrained. The [model card](https://thinkingmachines.ai/model-card/tml-d24-varloop-research/) gives later-midtraining sampling 1:2:6:2:1 and post-training at 3.

## Main, separate KV

| Domain or level | Passes | Cache | Run | Correct / n | Accuracy, 95% Wilson CI (%) | Mean / median reasoning tokens | Request s / correct | Batch GPU s / correct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MATH overall | 1 | separate | 0 | 185/200 | 92.5% [88.0, 95.4] | 1,096.9 / 320.0 | 12.870 | 0.600 |
| MATH level 1 | 1 | separate | 0 | 39/40 | 97.5% [87.1, 99.6] | 434.1 / 111.0 | 4.511 | — |
| MATH level 2 | 1 | separate | 0 | 39/40 | 97.5% [87.1, 99.6] | 569.8 / 206.0 | 6.528 | — |
| MATH level 3 | 1 | separate | 0 | 37/40 | 92.5% [80.1, 97.4] | 1,139.1 / 393.0 | 13.853 | — |
| MATH level 4 | 1 | separate | 0 | 37/40 | 92.5% [80.1, 97.4] | 1,387.2 / 419.5 | 16.330 | — |
| MATH level 5 | 1 | separate | 0 | 33/40 | 82.5% [68.1, 91.3] | 1,954.1 / 614.5 | 25.262 | — |
| MATH overall | 2 | separate | 0 | 192/200 | 96.0% [92.3, 98.0] | 820.6 / 278.5 | 13.154 | 0.637 |
| MATH level 1 | 2 | separate | 0 | 40/40 | 100.0% [91.2, 100.0] | 248.2 / 110.0 | 4.099 | — |
| MATH level 2 | 2 | separate | 0 | 40/40 | 100.0% [91.2, 100.0] | 291.9 / 221.5 | 4.983 | — |
| MATH level 3 | 2 | separate | 0 | 39/40 | 97.5% [87.1, 99.6] | 940.3 / 343.0 | 15.287 | — |
| MATH level 4 | 2 | separate | 0 | 37/40 | 92.5% [80.1, 97.4] | 1,102.1 / 344.0 | 17.620 | — |
| MATH level 5 | 2 | separate | 0 | 36/40 | 90.0% [76.9, 96.0] | 1,520.3 / 533.0 | 25.393 | — |
| MATH overall | 3 | separate | 0 | 198/200 | 99.0% [96.4, 99.7] | 642.4 / 269.0 | 13.719 | 0.685 |
| MATH level 1 | 3 | separate | 0 | 40/40 | 100.0% [91.2, 100.0] | 245.2 / 106.5 | 5.527 | — |
| MATH level 2 | 3 | separate | 0 | 40/40 | 100.0% [91.2, 100.0] | 261.7 / 183.5 | 6.111 | — |
| MATH level 3 | 3 | separate | 0 | 40/40 | 100.0% [91.2, 100.0] | 881.6 / 335.5 | 18.506 | — |
| MATH level 4 | 3 | separate | 0 | 40/40 | 100.0% [91.2, 100.0] | 610.1 / 361.5 | 13.362 | — |
| MATH level 5 | 3 | separate | 0 | 38/40 | 95.0% [83.5, 98.6] | 1,213.2 / 510.0 | 25.688 | — |
| MATH overall | 4 | separate | 0 | 195/200 | 97.5% [94.3, 98.9] | 715.8 / 279.5 | 18.461 | 0.962 |
| MATH level 1 | 4 | separate | 0 | 40/40 | 100.0% [91.2, 100.0] | 308.4 / 101.5 | 8.035 | — |
| MATH level 2 | 4 | separate | 0 | 40/40 | 100.0% [91.2, 100.0] | 263.1 / 191.5 | 7.428 | — |
| MATH level 3 | 4 | separate | 0 | 40/40 | 100.0% [91.2, 100.0] | 750.5 / 335.0 | 19.899 | — |
| MATH level 4 | 4 | separate | 0 | 39/40 | 97.5% [87.1, 99.6] | 730.4 / 336.5 | 18.994 | — |
| MATH level 5 | 4 | separate | 0 | 36/40 | 90.0% [76.9, 96.0] | 1,526.5 / 508.5 | 40.131 | — |
| MATH overall | 5 | separate | 0 | 195/200 | 97.5% [94.3, 98.9] | 697.1 / 276.0 | 21.189 | 1.219 |
| MATH level 1 | 5 | separate | 0 | 40/40 | 100.0% [91.2, 100.0] | 238.8 / 98.0 | 7.544 | — |
| MATH level 2 | 5 | separate | 0 | 40/40 | 100.0% [91.2, 100.0] | 294.9 / 193.5 | 9.818 | — |
| MATH level 3 | 5 | separate | 0 | 39/40 | 97.5% [87.1, 99.6] | 763.8 / 329.0 | 24.016 | — |
| MATH level 4 | 5 | separate | 0 | 39/40 | 97.5% [87.1, 99.6] | 887.6 / 323.5 | 25.320 | — |
| MATH level 5 | 5 | separate | 0 | 37/40 | 92.5% [80.1, 97.4] | 1,300.1 / 497.0 | 40.902 | — |
| MATH overall | 6 | separate | 0 | 196/200 | 98.0% [95.0, 99.2] | 720.1 / 278.0 | 25.758 | 1.338 |
| MATH level 1 | 6 | separate | 0 | 40/40 | 100.0% [91.2, 100.0] | 255.9 / 109.5 | 9.510 | — |
| MATH level 2 | 6 | separate | 0 | 39/40 | 97.5% [87.1, 99.6] | 487.7 / 186.0 | 16.582 | — |
| MATH level 3 | 6 | separate | 0 | 40/40 | 100.0% [91.2, 100.0] | 789.1 / 300.5 | 28.684 | — |
| MATH level 4 | 6 | separate | 0 | 40/40 | 100.0% [91.2, 100.0] | 741.7 / 359.0 | 27.278 | — |
| MATH level 5 | 6 | separate | 0 | 37/40 | 92.5% [80.1, 97.4] | 1,325.9 / 443.5 | 48.191 | — |
| GSM8K overall | 1 | separate | 0 | 142/150 | 94.7% [89.8, 97.3] | 396.3 / 222.5 | 4.511 | 0.317 |
| GSM8K overall | 2 | separate | 0 | 145/150 | 96.7% [92.4, 98.6] | 285.7 / 195.0 | 5.203 | 0.197 |
| GSM8K overall | 3 | separate | 0 | 145/150 | 96.7% [92.4, 98.6] | 277.1 / 178.5 | 6.751 | 0.242 |
| GSM8K overall | 4 | separate | 0 | 145/150 | 96.7% [92.4, 98.6] | 284.9 / 181.0 | 8.103 | 0.353 |
| GSM8K overall | 5 | separate | 0 | 145/150 | 96.7% [92.4, 98.6] | 266.9 / 184.0 | 9.349 | 0.331 |
| HumanEval overall | 1 | separate | 0 | 132/164 | 80.5% [73.8, 85.8] | 1,868.5 / 731.5 | 29.838 | 1.220 |
| HumanEval overall | 2 | separate | 0 | 154/164 | 93.9% [89.1, 96.7] | 1,294.5 / 675.0 | 26.356 | 1.118 |
| HumanEval overall | 3 | separate | 0 | 157/164 | 95.7% [91.5, 97.9] | 1,089.1 / 566.5 | 31.042 | 1.263 |
| HumanEval overall | 4 | separate | 0 | 157/164 | 95.7% [91.5, 97.9] | 1,088.6 / 595.5 | 36.625 | 1.654 |
| HumanEval overall | 5 | separate | 0 | 156/164 | 95.1% [90.7, 97.5] | 1,242.3 / 637.0 | 50.608 | 2.089 |
| BBH, five tasks overall | 1 | separate | 0 | 44/60 | 73.3% [61.0, 82.9] | 1,972.3 / 918.0 | 26.479 | 1.853 |
| BBH, five tasks overall | 3 | separate | 0 | 55/60 | 91.7% [81.9, 96.4] | 1,473.7 / 648.5 | 29.117 | 2.497 |
| BBH, five tasks overall | 5 | separate | 0 | 57/60 | 95.0% [86.3, 98.3] | 1,165.7 / 607.5 | 31.386 | 3.084 |
| SimpleQA Verified overall | 1 | separate | 0 | 14/200 | 7.0% [4.2, 11.4] | 1,577.5 / 603.5 | 276.894 | 11.277 |
| SimpleQA Verified overall | 3 | separate | 0 | 10/200 | 5.0% [2.7, 9.0] | 1,033.6 / 464.5 | 465.662 | 22.617 |
| SimpleQA Verified overall | 5 | separate | 0 | 11/200 | 5.5% [3.1, 9.6] | 829.2 / 417.0 | 478.222 | 25.386 |

## Shared KV

| Domain or level | Passes | Cache | Run | Correct / n | Accuracy, 95% Wilson CI (%) | Mean / median reasoning tokens | Request s / correct | Batch GPU s / correct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MATH overall | 3 | shared | 0 | 197/200 | 98.5% [95.7, 99.5] | 591.7 / 279.0 | 12.281 | 0.617 |
| MATH level 1 | 3 | shared | 0 | 40/40 | 100.0% [91.2, 100.0] | 228.3 / 100.0 | 5.023 | — |
| MATH level 2 | 3 | shared | 0 | 39/40 | 97.5% [87.1, 99.6] | 242.8 / 208.0 | 5.660 | — |
| MATH level 3 | 3 | shared | 0 | 40/40 | 100.0% [91.2, 100.0] | 745.6 / 323.5 | 15.348 | — |
| MATH level 4 | 3 | shared | 0 | 40/40 | 100.0% [91.2, 100.0] | 642.6 / 358.5 | 13.280 | — |
| MATH level 5 | 3 | shared | 0 | 38/40 | 95.0% [83.5, 98.6] | 1,099.0 / 565.0 | 22.436 | — |
| MATH overall | 5 | shared | 0 | 195/200 | 97.5% [94.3, 98.9] | 657.7 / 275.5 | 19.770 | 1.158 |
| MATH level 1 | 5 | shared | 0 | 40/40 | 100.0% [91.2, 100.0] | 283.2 / 104.5 | 8.568 | — |
| MATH level 2 | 5 | shared | 0 | 40/40 | 100.0% [91.2, 100.0] | 300.6 / 188.0 | 9.939 | — |
| MATH level 3 | 5 | shared | 0 | 40/40 | 100.0% [91.2, 100.0] | 603.9 / 298.0 | 19.470 | — |
| MATH level 4 | 5 | shared | 0 | 39/40 | 97.5% [87.1, 99.6] | 746.7 / 335.5 | 21.599 | — |
| MATH level 5 | 5 | shared | 0 | 36/40 | 90.0% [76.9, 96.0] | 1,354.3 / 470.5 | 41.491 | — |
| HumanEval overall | 3 | shared | 0 | 156/164 | 95.1% [90.7, 97.5] | 1,123.3 / 627.5 | 30.968 | 1.341 |
| HumanEval overall | 5 | shared | 0 | 154/164 | 93.9% [89.1, 96.7] | 1,051.0 / 565.5 | 43.480 | 1.752 |

## Extra repeat 1

| Domain or level | Passes | Cache | Run | Correct / n | Accuracy, 95% Wilson CI (%) | Mean / median reasoning tokens | Request s / correct | Batch GPU s / correct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MATH overall | 1 | separate | 1 | 93/100 | 93.0% [86.3, 96.6] | 1,132.3 / 366.0 | 11.477 | 0.819 |
| MATH level 1 | 1 | separate | 1 | 19/20 | 95.0% [76.4, 99.1] | 709.5 / 109.0 | 6.660 | — |
| MATH level 2 | 1 | separate | 1 | 19/20 | 95.0% [76.4, 99.1] | 854.4 / 363.0 | 8.604 | — |
| MATH level 3 | 1 | separate | 1 | 19/20 | 95.0% [76.4, 99.1] | 1,373.1 / 574.5 | 14.040 | — |
| MATH level 4 | 1 | separate | 1 | 18/20 | 90.0% [69.9, 97.2] | 1,237.5 / 354.5 | 12.764 | — |
| MATH level 5 | 1 | separate | 1 | 18/20 | 90.0% [69.9, 97.2] | 1,487.1 / 471.5 | 15.600 | — |
| MATH overall | 3 | separate | 1 | 98/100 | 98.0% [93.0, 99.4] | 715.7 / 318.5 | 13.225 | 1.099 |
| MATH level 1 | 3 | separate | 1 | 20/20 | 100.0% [83.9, 100.0] | 367.8 / 110.0 | 6.944 | — |
| MATH level 2 | 3 | separate | 1 | 20/20 | 100.0% [83.9, 100.0] | 324.8 / 216.5 | 7.138 | — |
| MATH level 3 | 3 | separate | 1 | 19/20 | 95.0% [76.4, 99.1] | 1,134.8 / 439.5 | 21.131 | — |
| MATH level 4 | 3 | separate | 1 | 20/20 | 100.0% [83.9, 100.0] | 478.3 / 264.5 | 10.044 | — |
| MATH level 5 | 3 | separate | 1 | 19/20 | 95.0% [76.4, 99.1] | 1,273.0 / 454.5 | 21.687 | — |
| HumanEval overall | 1 | separate | 1 | 133/164 | 81.1% [74.4, 86.4] | 1,871.0 / 711.5 | 29.761 | 1.201 |
| HumanEval overall | 3 | separate | 1 | 154/164 | 93.9% [89.1, 96.7] | 1,218.1 / 582.0 | 32.991 | 1.482 |

## Extra repeat 2

| Domain or level | Passes | Cache | Run | Correct / n | Accuracy, 95% Wilson CI (%) | Mean / median reasoning tokens | Request s / correct | Batch GPU s / correct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MATH overall | 1 | separate | 2 | 93/100 | 93.0% [86.3, 96.6] | 1,139.0 / 362.0 | 11.892 | 0.809 |
| MATH level 1 | 1 | separate | 2 | 20/20 | 100.0% [83.9, 100.0] | 461.5 / 115.5 | 4.796 | — |
| MATH level 2 | 1 | separate | 2 | 18/20 | 90.0% [69.9, 97.2] | 1,147.0 / 326.0 | 11.596 | — |
| MATH level 3 | 1 | separate | 2 | 17/20 | 85.0% [64.0, 94.8] | 1,804.9 / 513.5 | 20.007 | — |
| MATH level 4 | 1 | separate | 2 | 20/20 | 100.0% [83.9, 100.0] | 769.5 / 354.5 | 8.488 | — |
| MATH level 5 | 1 | separate | 2 | 18/20 | 90.0% [69.9, 97.2] | 1,512.3 / 471.5 | 16.191 | — |
| MATH overall | 3 | separate | 2 | 98/100 | 98.0% [93.0, 99.4] | 674.4 / 308.0 | 12.361 | 1.078 |
| MATH level 1 | 3 | separate | 2 | 20/20 | 100.0% [83.9, 100.0] | 331.4 / 115.5 | 6.365 | — |
| MATH level 2 | 3 | separate | 2 | 20/20 | 100.0% [83.9, 100.0] | 296.5 / 197.0 | 6.564 | — |
| MATH level 3 | 3 | separate | 2 | 19/20 | 95.0% [76.4, 99.1] | 1,090.7 / 512.5 | 19.558 | — |
| MATH level 4 | 3 | separate | 2 | 20/20 | 100.0% [83.9, 100.0] | 435.2 / 238.5 | 9.143 | — |
| MATH level 5 | 3 | separate | 2 | 19/20 | 95.0% [76.4, 99.1] | 1,218.2 / 447.0 | 20.966 | — |
| HumanEval overall | 1 | separate | 2 | 135/164 | 82.3% [75.8, 87.4] | 1,836.7 / 731.5 | 28.529 | 1.168 |
| HumanEval overall | 3 | separate | 2 | 154/164 | 93.9% [89.1, 96.7] | 1,144.8 / 566.5 | 31.059 | 1.404 |

The [CSV](results/publication/full-results.csv) retains training labels, API reasoning counts, answer lengths, truncations, and the other metrics. The [JSON](results/publication/analysis.json) also contains paired tests and bootstrap results.
