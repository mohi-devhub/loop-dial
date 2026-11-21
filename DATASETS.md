# Dataset redistribution decisions

All five dataset sources were checked against primary repositories or publisher metadata. Source notices are preserved in `licenses/`. The study includes only the selected examples, not model weights or unrelated benchmark releases.

| Dataset | Evidence | Decision |
| --- | --- | --- |
| GSM8K | [OpenAI MIT licence](https://github.com/openai/grade-school-math/blob/3101c7d5072418e28b9008a6636bde82a006892c/LICENSE) | Include selected problem text, reference answers and model outputs, with the OpenAI notice. |
| MATH-500 | [H4 card](https://huggingface.co/datasets/HuggingFaceH4/MATH-500/blob/6e4ed1a2a79af7d8630a6b768ec859cb5af4d3be/README.md) points to [PRM800K](https://github.com/openai/prm800k), which has an MIT licence; [original MATH](https://github.com/hendrycks/math/blob/main/LICENSE) also has MIT | Include selected problems, answers, solutions and model outputs with both upstream notices. The H4 card itself has no licence field; this decision follows its declared source chain rather than inventing an H4-specific licence. |
| HumanEval | [OpenAI MIT licence at the pinned revision](https://github.com/openai/human-eval/blob/b9453e8f1865df0a0057a1383767caa400acfbcf/LICENSE) | Include all 164 prompts and tests, and the generated code, with the OpenAI notice. Generated code is data and is not executed by CPU reproduction. |
| BBH, five tasks | [MIT licence at the pinned BBH revision](https://github.com/suzgunmirac/BIG-Bench-Hard/blob/9ee07bd481feebf959a6b59d61ea57bdcf30964d/LICENSE) | Include the 60 selected prompts, labels and model outputs with the BBH notice. The tasks are boolean expressions, multistep arithmetic, seven-object logical deduction and tracking, and Dyck languages. |
| SimpleQA Verified | [Google publisher card at the pinned revision](https://huggingface.co/datasets/google/simpleqa-verified/blob/0dc97e0d28d8233463e005cdc4475cc2a13ba2dc/README.md) explicitly declares `license: mit` | Include the selected 200 questions, gold answers and model outputs with attribution to the dataset authors. There is no standalone LICENSE file at that revision; the publisher metadata is the licence declaration. |

The selected IDs, source revisions and hashes are in the dataset manifests. `scripts/fetch_datasets.py` can fetch the original sources and checks their hashes. No dataset requires an IDs-only fallback under the checked declarations. This repository does not relabel third-party material as newly authored study code.

The checkpoint's publisher declares Apache 2.0. We distribute no weights. See the [research checkpoint card](https://huggingface.co/thinkingmachines/TML-d24-varloop-research) and the [Thinking Machines model card](https://thinkingmachines.ai/model-card/tml-d24-varloop-research/).
