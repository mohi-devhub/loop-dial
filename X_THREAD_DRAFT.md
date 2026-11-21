# X thread draft

Six posts. Nothing has been posted. The blog is the main link and the repository is the second link. All three charts include our own measurements; the knowledge chart also contains a separately labeled publisher reference.

## 1/6

Loop Dial: I varied inference depth on thinkingmachines/TML-d24-varloop-research, the varloop research checkpoint. 5,334 scored responses on fixed subsets.
https://mohith.xyz/blog/loop-dial
https://github.com/mohi-devhub/loop-dial

## 2/6

On our 200-problem MATH subset, accuracy was 92.5% at 1 pass and 99.0% at 3 (95% CI 96.4–99.7). At 4, 5 and 6 it was 97.5%, 97.5% and 98.0%. Paired tests found no clear gain beyond 3. This is a small, near-ceiling sample.

## 3/6

From 1 to 3 passes, mean reasoning text used 41% fewer tokens on MATH and 42% fewer on code. Among answers correct at both depths, the drops were 28% and 20%. That shows shorter writing; it does not reveal what the internal loops computed.

Attachment: [reasoning-tokens-vs-passes.png](results/publication/charts/reasoning-tokens-vs-passes.png)

## 4/6

Shorter writing was not always faster. On MATH, GPU time per correct answer went from 0.69s at 3 passes to 1.34s at 6. These are batched C32 costs, excluding loading and grading. More passes cost more without a clear MATH score gain here.

Attachment: [cost-per-correct-vs-passes.png](results/publication/charts/cost-per-correct-vs-passes.png)

## 5/6

MATH level 5 still had headroom: 38/40 correct at 3 passes, with a wide 95% CI of 83.5–98.6%. Repeat accuracy ranges reached 1 point on MATH and 1.8 on code. Passes 4–5 are midtraining only; 6 is untrained. The checkpoint was post-trained at 3.
https://thinkingmachines.ai/model-card/tml-d24-varloop-research/

## 6/6

On 200 SimpleQA Verified questions, official grading gave 7.0%, 5.0%, 5.5% at 1/3/5 passes. Paired 1-vs-3 McNemar p=0.289. One run per depth cannot establish knowledge equivalence. The chart shows our 95% CIs; gray is publisher context only.

Attachment: [knowledge-control-context.png](results/publication/charts/knowledge-control-context.png)
