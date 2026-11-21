# Third-party notices

The root MIT licence applies to original study code and authored study material. Benchmark text, reference answers, tests and source solutions retain their upstream terms. Preserve these notices when redistributing those parts.

- GSM8K: Copyright (c) 2021 OpenAI. MIT. Full notice: [gsm8k.txt](licenses/gsm8k.txt).
- HumanEval: Copyright (c) OpenAI. MIT. Full notice: [human_eval.txt](licenses/human_eval.txt).
- MATH: Copyright (c) 2021 Dan Hendrycks. MIT. Full notice: [math_original.txt](licenses/math_original.txt).
- PRM800K / MATH split: Copyright (c) 2023 OpenAI. MIT. Full notice: [prm_license.txt](licenses/prm_license.txt).
- BIG-Bench Hard: Copyright (c) 2022 suzgunmirac. MIT. Full notice: [bbh.txt](licenses/bbh.txt).
- SimpleQA Verified: Lukas Haas, Gal Yona, Giovanni D’Antonio, Sasha Goldshtein and Dipanjan Das, Google DeepMind and Google Research. The publisher declares MIT in the [saved dataset card](licenses/simpleqa_card.txt). Cite *SimpleQA Verified: A Reliable Factuality Benchmark to Measure Parametric Knowledge*, arXiv:2509.07968.

Model outputs are generated study artifacts, separate from upstream gold solutions. The model publisher's Apache 2.0 declaration is not a licence grant over dataset material. We do not redistribute model weights or the full publisher web page. Publisher score tables contain extracted numeric facts with a model-card citation.

The complete official grading notebook and its prompt text are fetched from the original source by the grading preparation script; they are not vendored into this export because its standalone notebook licence was not exposed by the source metadata we checked. Saved official grades and usage are included in the scored results, so CPU reproduction does not need the grader prompt or an API call.

Python and JavaScript packages are dependencies, not vendored source. Their upstream licences remain applicable.
