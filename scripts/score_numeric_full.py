#!/usr/bin/env python3
"""Grade math and BBH locally as immutable inference outputs arrive."""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import time

from math_equivalence import extract_final, grade_math


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/full"


def grade_reasoning(answer, expected, task, finish_reason):
    if task == "multistep_arithmetic_two":
        return grade_math(answer, expected, "math", finish_reason)
    prediction = extract_final(answer)
    if task == "dyck_languages":
        text = answer.strip()
        if r"\boxed{" in text and text.endswith("}"):
            text = text[text.rfind(r"\boxed{") + 7:-1]
        text = re.sub(r"\\(?:text|mathrm)\{(.*)\}", r"\1", text, flags=re.S)
        normalized = "".join(x for x in text if x in "()[]{}<>")
        correct = normalized == "".join(expected.split())
    elif task == "boolean_expressions":
        values = re.findall(r"\b(true|false)\b", prediction, flags=re.I)
        normalized = values[-1].lower() if len(set(x.lower() for x in values)) == 1 else ""
        correct = normalized == expected.lower()
    else:
        matched = re.fullmatch(r"\s*\(?([A-Za-z])\)?[.]?\s*", prediction)
        normalized = matched[1].upper() if matched else ""
        correct = normalized == expected.strip("() ").upper()
    return {"correct": correct and finish_reason != "length", "raw_string_match": prediction == expected, "extracted_answer": prediction, "normalized_answer": normalized, "grader_version": "loop-dial-bbh-v1", "truncated": finish_reason == "length"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--follow", action="store_true")
    args = parser.parse_args()
    (OUT / "numeric-scorer-process.json").write_text(json.dumps({"pid": os.getpid(), "started_epoch": time.time()}))
    dest = OUT / "numeric-scores.jsonl"
    seen = {json.loads(x)["key"] for x in dest.read_text().splitlines()} if dest.exists() else set()
    counts = Counter()
    graded_count = 0
    stream = None
    buffer = ""
    while True:
        source = OUT / "outputs.jsonl"
        if stream is None and source.exists():
            stream = source.open()
        chunk = stream.readline() if stream else ""
        if chunk:
            buffer += chunk
            if not buffer.endswith("\n"):
                continue
            row = json.loads(buffer)
            buffer = ""
            counts[row["phase"]] += 1
            key = row["phase"] + ":" + row["id"]
            if row["domain"] != "humaneval" and key not in seen:
                result = {"key": key, "domain": row["domain"], "id": row["id"], "passes": row["passes"], "repeat": row["repeat"], "share_cache": row["share_cache"], "level": row["level"]}
                if row.get("error"):
                    result.update(correct=None, inference_error=row["error"])
                elif row["domain"] in ["math", "gsm8k"]:
                    result.update(grade_math(row["answer"], row["expected_answer"], row["domain"], row["finish_reason"]))
                else:
                    result.update(grade_reasoning(row["answer"], row["expected_answer"], row["task"], row["finish_reason"]))
                with dest.open("a") as output:
                    output.write(json.dumps(result) + "\n")
                seen.add(key)
                graded_count += 1
            status = {"counts": dict(counts), "raw_outputs_processed": sum(counts.values()), "numeric_records_saved": len(seen), "last_phase": row["phase"], "last_id": row["id"], "updated_epoch": time.time()}
            temporary = OUT / "numeric-progress.tmp"
            temporary.write_text(json.dumps(status))
            temporary.replace(OUT / "numeric-progress.json")
            continue
        state_path = OUT / "job-state.json"
        terminal = state_path.exists() and json.loads(state_path.read_text())["stage"] in ["COMPLETED", "ERROR", "CANCELED", "CANCELLED"]
        if not args.follow or terminal:
            break
        time.sleep(2)
    print(json.dumps({"newly_graded": graded_count, "raw_outputs_processed": sum(counts.values()), "numeric_records_saved": len(seen)}))


if __name__ == "__main__":
    main()
