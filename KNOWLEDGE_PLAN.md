# Approved SimpleQA Verified control

The user approved **200 questions at passes 1, 3 and 5**, official grading, with a **$5 combined incremental cap**. This replaces the earlier proposed $9 cap. No other inference is authorized.

The checkpoint is **thinkingmachines/TML-d24-varloop-research**, the varloop research checkpoint, pinned to the same revision and SGLang image as the completed study. The fixed 200-question subset is selected from all 1,000 questions by SHA-256 ranking with seed 20261121. [The manifest](data/knowledge/manifest.json) publishes every selected ID, source revision, prompt hash and grading-source hash.

The generation prompt is the bare question, matching the official starter. No search, retrieval or tools are supplied. Temperature is zero, seed 1729, concurrency 32, output limit 8,192 tokens and context limit 16,384. Each depth uses a fresh server and separate KV cache. Execution order is 3, 1, 5. One 64-token warmup at each depth is excluded from the 600 scored outputs.

Grading uses the exact [official SimpleQA Verified template](https://www.kaggle.com/code/nanliao7/simpleqa-verified-benchmark-starter-code) with **gpt-4.1-2025-04-14**. The final answer channel is graded; visible reasoning is excluded. The rubric distinguishes CORRECT, INCORRECT and NOT_ATTEMPTED, including the supplied numeric tolerances. Accuracy is CORRECT / 200. An invalid judge response stops scoring rather than silently changing the score. Identical complete grading prompts reuse the same judgment, preventing inconsistent grades for identical final answers.

The official rubric and pinned model run through the [OpenAI Batch API](https://developers.openai.com/api/docs/guides/batch), which costs 50% less than synchronous calls and may take up to 24 hours. Judge temperature is zero and the response allowance is 16 tokens for its required A/B/C letter. These are execution settings around the official rubric. The rubric source is saved without executing the starter notebook.

At the checked HF rate of $0.045833/minute, the GPU controller cancels after 55 minutes, with a two-minute cleanup allowance: **$2.612481** maximum planned GPU liability. The grading reserve is **$2.20**, giving **$4.812481** combined planned liability. Worker and provider deadlines are earlier. The complete grading batch is token-counted before submission; it is refused if its conservative liability exceeds its reserve or the combined $5 cap. There are no automatic paid retries. At the forecast output length of 1,024 tokens, generation plus Batch grading is approximately **$2.3**, subject to actual response lengths and runtime.

The report will include per-pass accuracy with Wilson 95% intervals, reasoning and answer token summaries, batch timing and costs. The requested paired comparison is one versus three passes: exact two-sided McNemar for accuracy and a paired bootstrap interval for reasoning-token differences, with 10,000 draws and seed 271828. Additional depth comparisons are exploratory. A nonsignificant test will not establish knowledge equivalence.

The knowledge chart will show our own estimates and confidence intervals, with the model-card point estimates as a separate reference line. The model card uses a different evaluation protocol and sample. Our checkpoint must never be labeled as shipped Inkling 2 Mini.

The OpenAI credential is loaded locally from the user-provided ignored `.env` file. It is excluded from the GPU bundle, logs, manifests and API request artifacts. Actual invoices remain distinct from timestamp- and usage-based cost estimates.
