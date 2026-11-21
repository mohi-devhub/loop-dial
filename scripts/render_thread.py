#!/usr/bin/env python3
"""Write six posts and chart attachments. Never posts or starts compute."""

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def main():
    a = json.loads((ROOT / "results/full/analysis.json").read_text())
    pub = json.loads((ROOT / "results/publication/analysis.json").read_text())
    card = json.loads((ROOT / "results/publication/model-card-context.json").read_text())
    assert pub["knowledge_control"]["status"] in ["not run", "complete"]
    knowledge_path = ROOT / "results/knowledge/analysis.json"
    knowledge = json.loads(knowledge_path.read_text()) if knowledge_path.exists() else None
    r = {(c["domain"], c["passes"]): c for c in a["conditions"] if not c["share_cache"] and c["repeat"] == 0}
    pairs = {p["domain"]: p for p in a["paired_comparisons"] if p["comparison"] == "separate" and p["from_passes"] == 1 and p["to_passes"] == 3}
    m3 = r[("math", 3)]
    l5 = next(c for c in pub["level5_ceiling"] if c["passes"] == 3)
    noise = {d: max(n["accuracy_range_pp"] for n in a["repeat_noise"] if n["domain"] == d) for d in ["math", "humaneval"]}
    sq = next(c for c in card["publisher_scores"] if c["benchmark"] == "SimpleQA Verified")["publisher_percent_by_pass"]
    tweets = [
        "We tested inference depth on thinkingmachines/TML-d24-varloop-research: 4,734 saved responses on fixed math, code and reasoning subsets. This is the varloop research checkpoint, not shipped Inkling 2 Mini.\nhttps://thinkingmachines.ai/model-card/tml-d24-varloop-research/",
        f"On our 200-problem MATH subset, accuracy was {r[('math',1)]['accuracy']*100:.1f}% at 1 pass and {m3['accuracy']*100:.1f}% at 3 (95% CI {m3['wilson_95'][0]*100:.1f}–{m3['wilson_95'][1]*100:.1f}). At 4, 5 and 6 it was {r[('math',4)]['accuracy']*100:.1f}%, {r[('math',5)]['accuracy']*100:.1f}% and {r[('math',6)]['accuracy']*100:.1f}%. Paired tests found no clear gain beyond 3. This is a small, near-ceiling sample.",
        f"From 1 to 3 passes, mean reasoning text used {-pairs['math']['reasoning_tokens']['relative_mean_change']*100:.0f}% fewer tokens on MATH and {-pairs['humaneval']['reasoning_tokens']['relative_mean_change']*100:.0f}% fewer on code. Among answers correct at both depths, the drops were {-pairs['math']['reasoning_sensitivity']['both_correct']['relative_mean_change']*100:.0f}% and {-pairs['humaneval']['reasoning_sensitivity']['both_correct']['relative_mean_change']*100:.0f}%. That shows shorter writing; it does not reveal what the internal loops computed.",
        f"Shorter writing was not always faster. On MATH, GPU time per correct answer went from {m3['gpu_seconds_per_correct']:.2f}s at 3 passes to {r[('math',6)]['gpu_seconds_per_correct']:.2f}s at 6. These are batched C32 costs, excluding loading and grading. More passes cost more without a clear MATH score gain here.",
        f"MATH level 5 still had headroom: {l5['correct']}/{l5['n_scored']} correct at 3 passes, with a wide 95% CI of {l5['wilson_95'][0]*100:.1f}–{l5['wilson_95'][1]*100:.1f}%. Repeat accuracy ranges reached {noise['math']:.0f} point on MATH and {noise['humaneval']:.1f} on code. Passes 4–5 are midtraining only; 6 is untrained. The checkpoint was post-trained at 3.",
        f"We did not run the SimpleQA Verified knowledge control. The model card reports {sq['1']:.1f}%, {sq['3']:.1f}% and {sq['5']:.1f}% at 1, 3 and 5 passes. Those are publisher results, not our replication. We cannot claim that knowledge stayed flat in our study. The third chart is context only.",
    ]
    if knowledge:
        conditions = sorted(knowledge["conditions"], key=lambda r: r["passes"])
        pair = knowledge["paired_comparisons"][0]
        p = pair["mcnemar"]["exact_two_sided_p"]
        scores = ", ".join(f"{r['accuracy']*100:.1f}%" for r in conditions)
        tweets[0] = tweets[0].replace("4,734 saved responses", "5,334 saved responses").replace("math, code and reasoning subsets", "math, code, reasoning and knowledge subsets")
        tweets[5] = f"On 200 SimpleQA Verified questions, official grading gave {scores} at 1/3/5 passes. Paired 1-vs-3 McNemar p={p:.3g}. One run per depth cannot establish knowledge equivalence. The chart shows our 95% CIs; gray is publisher context only."
    total = a["n_outputs"] + (knowledge["scored_outputs"] if knowledge else 0)
    tweets[0] = f"Loop Dial: I varied inference depth on thinkingmachines/TML-d24-varloop-research, the varloop research checkpoint. {total:,} scored responses on fixed subsets.\nhttps://github.com/mohi-devhub/loop-dial"
    tweets[4], tweets[5] = tweets[5], tweets[4]
    tweets[4] += "\nhttps://thinkingmachines.ai/model-card/tml-d24-varloop-research/"
    tweets[5] += "\nhttps://mohith.xyz/blog/loop-dial"
    lengths = [len(re.sub(r"https?://\S+", "x" * 23, t)) for t in tweets]
    assert all(n <= 280 for n in lengths), lengths
    attachments = {3: "results/publication/charts/reasoning-tokens-vs-passes.png", 4: "results/publication/charts/cost-per-correct-vs-passes.png", 5: "results/publication/charts/knowledge-control-context.png"}
    lines = ["# X thread draft", "", "Six posts. Nothing has been posted. Add the public report URL before publication. The knowledge control is missing; its chart contains publisher data only. Use the first two charts alone if you prefer not to include external context.", ""]
    if knowledge:
        lines[2] = "Six posts. Nothing has been posted. The repository is linked in post 1. The blog URL is last in post 6, which has no image attachment so its preview card can appear. All three charts include our own measurements; the knowledge chart also contains a separately labeled publisher reference."
    for i, tweet in enumerate(tweets, 1):
        lines += [f"## {i}/6", "", tweet, ""]
        if i in attachments:
            lines += ["Attachment: [" + Path(attachments[i]).name + "](" + attachments[i] + ")", ""]
    (ROOT / "X_THREAD_DRAFT.md").write_text("\n".join(lines))
    (ROOT / "results/full/thread-lengths.json").write_text(json.dumps({"tweet_count": 6, "approximate_lengths_with_urls_as_23": lengths, "posted": False, "attachments": attachments, "knowledge_chart_is_our_measurement": knowledge is not None}, indent=2) + "\n")
    print(json.dumps({"posts": 6, "maximum_length": max(lengths), "posted": False}))


if __name__ == "__main__":
    main()
