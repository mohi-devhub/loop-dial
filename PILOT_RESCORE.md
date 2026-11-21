# Pilot re-score under numeric equivalence

Checkpoint: **thinkingmachines/TML-d24-varloop-research, varloop research checkpoint**. These are the same saved pilot responses. No new GPU inference was used for re-scoring.

| Passes | Numeric equivalence | 95% Wilson CI | Literal string match | Legacy reference grader |
| --- | ---: | --- | ---: | ---: |
| 1 | 50/50, 100% | 92.9%–100% | 24/50, 48% | 44/50, 88% |
| 3 | 50/50, 100% | 92.9%–100% | 24/50, 48% | 44/50, 88% |
| 6 | 50/50, 100% | 92.9%–100% | 25/50, 50% | 47/50, 94% |

The primary grader (`loop-dial-math-equivalence-v2`) strips unit words and currency, normalizes fractions and decimals, and uses bounded SymPy-based equivalence for expressions. Literal string matching compares the last extracted boxed answer with the reference after outer whitespace removal, without numeric normalization. The prior reference score is retained for historical comparison. There were no grader errors in the 150 pilot outputs. The v2 re-score agrees with the earlier v1 re-score on all 150 saved responses.

GSM8K is saturated under the new primary metric, so the full study uses it to study written-reasoning length. The numeric-equivalence scores are not directly comparable to the cookbook's differently graded 84.0% and 88.5% figures.

For the original rough sanity check, the legacy 1-pass and 3-pass scores were both 88% (95% Wilson CI 76.2%–94.4%), encompassing the cookbook's 84.0% and 88.5%. Fifty problems provide weak evidence. The cookbook's loop-options paragraph does not pin its model revision, subset, or prompt, and our primary scoring protocol differs. Under the new numeric grader both scores are 100%, with intervals above those reference values; that does not constitute an exact reproduction of the cookbook.

The original outputs remain unchanged. Updated records and summaries are [rescored-numeric-v2.jsonl](results/pilot/rescored-numeric-v2.jsonl.gz) and [rescored-numeric-v2-summary.json](results/pilot/rescored-numeric-v2-summary.json). Grader source is [math_equivalence.py](scripts/math_equivalence.py); rerun with ` .venv/bin/python scripts/rescore_pilot_numeric.py`.
