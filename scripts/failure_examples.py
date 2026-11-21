#!/usr/bin/env python3
"""Extract higher-depth regressions on the same saved MATH problems."""

from collections import Counter
import json
from analyze_full import read_jsonl
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/full"


def repeated_phrase(text):
    words = text.split()
    counts = Counter(tuple(words[i:i + 8]) for i in range(max(0, len(words) - 7)))
    if not counts:
        return {"occurrences": 0, "phrase": ""}
    phrase, occurrences = counts.most_common(1)[0]
    return {"occurrences": occurrences, "phrase": " ".join(phrase)}


def main():
    rows = read_jsonl(OUT / "scored-outputs.jsonl")
    baseline = {r["id"]: r for r in rows if r["domain"] == "math" and r["passes"] == 3 and not r["share_cache"] and r["repeat"] == 0}
    examples = []
    for row in rows:
        if row["domain"] != "math" or row["passes"] < 4 or row["share_cache"] or row["repeat"] or row.get("correct") is not False:
            continue
        previous = baseline.get(row["id"], {})
        if previous.get("correct") is not True:
            continue
        phrase = repeated_phrase(row["reasoning"])
        examples.append({"checkpoint_label": row["checkpoint_label"], "id": row["id"], "level": row["level"], "passes": row["passes"], "training_regime": row["training_regime"], "prompt": row["prompt"], "expected_answer": row["expected_answer"], "baseline_passes": 3, "baseline_correct_answer": previous["answer"], "baseline_reasoning_tokens": previous["reasoning_tokens"], "higher_depth_answer": row["answer"], "higher_depth_reasoning_tokens": row["reasoning_tokens"], "finish_reason": row["finish_reason"], "repeated_8word_phrase": phrase, "reasoning_tail": row["reasoning"][-1200:], "failure_type": "repetition_until_token_limit" if row["finish_reason"] == "length" and phrase["occurrences"] >= 10 else "token_limit" if row["finish_reason"] == "length" else "wrong_final_answer"})
    (OUT / "failure-examples.json").write_text(json.dumps({"selection": "All MATH main-run problems correct at 3 passes and incorrect at a higher measured depth; descriptive, selected examples", "examples": examples}, indent=2) + "\n")
    print(json.dumps({"regressions": len(examples), "by_type": dict(Counter(r["failure_type"] for r in examples))}))


if __name__ == "__main__":
    main()
