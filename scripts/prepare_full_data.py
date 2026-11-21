#!/usr/bin/env python3
"""Freeze public datasets, stratified subsets, and the approved execution matrix."""

from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import urllib.request

from pilot_common import PROMPT, rank_id


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/full"
SOURCES = {
    "math.jsonl": "https://huggingface.co/datasets/HuggingFaceH4/MATH-500/resolve/6e4ed1a2a79af7d8630a6b768ec859cb5af4d3be/test.jsonl",
    "humaneval.jsonl.gz": "https://raw.githubusercontent.com/openai/human-eval/b9453e8f1865df0a0057a1383767caa400acfbcf/data/HumanEval.jsonl.gz",
}
TASKS = ["multistep_arithmetic_two", "logical_deduction_seven_objects", "tracking_shuffled_objects_seven_objects", "boolean_expressions", "dyck_languages"]
for task in TASKS:
    SOURCES[f"bbh-{task}.json"] = f"https://raw.githubusercontent.com/suzgunmirac/BIG-Bench-Hard/9ee07bd481feebf959a6b59d61ea57bdcf30964d/bbh/{task}.json"


def rank(domain, identifier):
    return hashlib.sha256(f"20261121:{domain}:{identifier}".encode()).hexdigest()


def fetch(pair):
    name, url = pair
    path = DATA / "sources" / name
    if not path.exists():
        with urllib.request.urlopen(url, timeout=45) as response:
            path.write_bytes(response.read())
    return {"file": str(path.relative_to(ROOT)), "url": url, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def item(domain, identifier, problem, expected, level=None, task=None):
    if domain in ["math", "gsm8k"]:
        prompt = PROMPT.format(problem)
    elif domain == "humaneval":
        prompt = "Complete the Python function below. Return only the complete Python code, including the supplied function signature, and no tests.\n\n" + problem
    else:
        prompt = "Solve this reasoning problem. Put only the final answer inside \\boxed{}. For a multiple-choice problem give its option letter.\n\n" + problem
    return {"domain": domain, "id": identifier, "problem": problem, "prompt": prompt, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "expected_answer": str(expected), "level": level, "task": task, "rank": rank(domain, identifier)}


def main():
    config = json.loads((ROOT / "full-config.json").read_text())
    (DATA / "sources").mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=7) as pool:
        source_manifest = list(pool.map(fetch, SOURCES.items()))
    math_all = [json.loads(x) for x in (DATA / "sources/math.jsonl").read_text().splitlines()]
    math = [item("math", x["unique_id"], x["problem"], x["answer"], x["level"]) for x in math_all]
    selected_math, repeated_math = [], []
    for level in range(1, 6):
        group = sorted([x for x in math if x["level"] == level], key=lambda x: x["rank"])
        assert len(group) >= 40
        selected_math.extend(group[:40])
        repeated_math.extend(group[:20])
    selected_math.sort(key=lambda x: x["rank"])
    repeated_math.sort(key=lambda x: x["rank"])
    gsm = []
    for i, row in enumerate((ROOT / "data/gsm8k-test.jsonl").read_text().splitlines()):
        row = json.loads(row)
        value = item("gsm8k", f"test:{i}", row["question"], row["answer"].split("####")[-1].strip())
        value["rank"] = rank_id(value["id"])
        gsm.append(value)
    gsm.sort(key=lambda x: x["rank"])
    gsm = gsm[:config["domain_counts"]["gsm8k"]]
    human = [json.loads(x) for x in gzip.decompress((DATA / "sources/humaneval.jsonl.gz").read_bytes()).decode().splitlines()]
    assert len(human) == 164
    code = [item("humaneval", x["task_id"], x["prompt"], "") for x in human]
    code.sort(key=lambda x: x["rank"])
    hard = []
    for task in TASKS:
        examples = json.loads((DATA / f"sources/bbh-{task}.json").read_text())["examples"]
        group = [item("bbh", f"{task}:{i}", x["input"], x["target"], task=task) for i, x in enumerate(examples)]
        group.sort(key=lambda x: x["rank"])
        hard.extend(group[:config["domain_counts"]["bbh"] // 5])
    hard.sort(key=lambda x: x["rank"])
    datasets = {"math": selected_math, "math-repeat": repeated_math, "gsm8k": gsm, "humaneval": code, "bbh": hard}
    for name, rows in datasets.items():
        assert len({x["id"] for x in rows}) == len(rows)
        for row in rows:
            assert len(row["prompt"].encode()) + 512 + config["max_tokens"] <= config["context_length"], row["id"]
        (DATA / f"{name}.json").write_text(json.dumps(rows, indent=2) + "\n")
    (DATA / "humaneval-tests.json").write_text(json.dumps(human, indent=2) + "\n")
    cases = []
    for p in config["execution_pass_order"]:
        domains = [d for d in ["math", "humaneval", "gsm8k", "bbh"] if p in config["main_passes"][d] and config["domain_counts"][d]]
        cases.append({"key": f"p{p}-separate-r0", "passes": p, "share_cache": False, "repeat": 0, "domains": domains})
    for p in config["shared_passes"]:
        cases.append({"key": f"p{p}-shared-r0", "passes": p, "share_cache": True, "repeat": 0, "domains": config["shared_domains"]})
    for r in range(1, config["additional_repeat_runs"] + 1):
        for p in config["repeat_passes"]:
            cases.append({"key": f"p{p}-separate-r{r}", "passes": p, "share_cache": False, "repeat": r, "domains": ["math", "humaneval"]})
    config["cases"] = cases
    (ROOT / "full-config.json").write_text(json.dumps(config, indent=2) + "\n")
    manifest = {"seed": config["subset_seed"], "sources": source_manifest, "hard_reasoning": "Public BIG-Bench-Hard; GPQA file access was unavailable with the Jobs-only token", "ids": {k: [x["id"] for x in v] for k, v in datasets.items()}, "prompt_hashes": {k: {x["id"]: x["prompt_sha256"] for x in v} for k, v in datasets.items()}, "math_levels": {str(i): sum(x["level"] == i for x in selected_math) for i in range(1, 6)}, "repeat_math_levels": {str(i): sum(x["level"] == i for x in repeated_math) for i in range(1, 6)}, "human_eval_prompt_mode": "chat, complete function including signature; official unit tests; no candidate execution locally"}
    (DATA / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"counts": {k: len(v) for k, v in datasets.items()}, "server_conditions": len(cases), "max_prompt_bytes": max(len(x["prompt"].encode()) for v in datasets.values() for x in v)}))


if __name__ == "__main__":
    main()
