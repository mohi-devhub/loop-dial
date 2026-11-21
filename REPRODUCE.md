# Reproduce the public study

Use Python 3.13. Install the pinned analysis dependencies, then run the offline entry point:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-analysis.txt
.venv/bin/python scripts/reproduce.py
```

The entry point disables socket connections before loading analysis scripts. It makes no GPU, model, paid-grader or sandbox calls. It regenerates the full and knowledge analyses, paired comparisons, difficulty and repeat statistics, failure-example selection, legacy GSM8K sanity check, tables, plots, reports, README and X draft. It checks numerical values against `reference/` with a tolerance of 1e-12. The references are comparison targets, not analysis inputs. A mismatch exits nonzero and is written to `results/reproduction.json`.

Inputs are the two compressed scored-output archives, recorded domain-batch timings, fixed subset manifests, archived grade labels and resource-cost records. Every reasoning and final-answer string is retained. Per-chunk timestamp arrays were replaced by their first and last time and count; reported decode-latency scalars are preserved. The public export omits raw server logs, personal account identifiers, workstation paths, caches and all credentials.

CPU reproduction recomputes statistics from saved scores. It does not claim to independently rerun HumanEval execution, numeric grading or the official SimpleQA judge. HumanEval candidates are never executed by this entry point. All 5,334 original graded outputs remain available for inspection.

To fetch the pinned original dataset sources, separately run `python scripts/fetch_datasets.py`. This needs network access, but no model weights. Selected problem text is already included under the licences documented in DATASETS.md. Grading and inference dependencies are in their separate requirement files; they are unnecessary for the offline analysis.

The original inference workers and budget controller are provided under scripts/. Archived configuration files are historical records, not new spend authorization, and the public launcher refuses them by default. No weights, API keys or account session files are included.

The clean-clone check initially exposed an undeclared `sgl_eval` import in the secondary cookbook comparison. That step now calculates its statistics from the archived legacy grade records, just as the primary analysis uses archived grades. The optional grading dependency is no longer part of CPU reproduction. No numerical values were changed.
