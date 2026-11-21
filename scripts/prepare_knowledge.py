#!/usr/bin/env python3
"""Freeze the approved factuality control and the official grading source."""

import ast
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path

import requests
import tiktoken


ROOT = Path(__file__).resolve().parents[1]
REVISION = "0dc97e0d28d8233463e005cdc4475cc2a13ba2dc"
SEED = 20261121
DATASET = "https://huggingface.co/datasets/google/simpleqa-verified"
NOTEBOOK = "https://www.kaggle.com/code/nanliao7/simpleqa-verified-benchmark-starter-code"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    evidence = ROOT / "evidence/knowledge"
    data_dir = ROOT / "data/knowledge"
    output = ROOT / "results/knowledge"
    for directory in [evidence, data_dir, output]:
        directory.mkdir(parents=True, exist_ok=True)
    assert not (output / "launch-intent.json").exists(), "Do not change a launched experiment"
    session = requests.Session()
    blobs = {}
    for filename in ["README.md", "simpleqa_verified.csv"]:
        response = session.get(f"{DATASET}/resolve/{REVISION}/{filename}", timeout=30)
        response.raise_for_status()
        blobs[filename] = response.content
        (evidence / filename).write_bytes(response.content)
    response = session.get("https://www.kaggle.com/api/v1/kernels/pull/nanliao7/simpleqa-verified-benchmark-starter-code", timeout=30)
    response.raise_for_status()
    notebook_response = response.json()
    notebook = json.loads(notebook_response["blob"]["source"])
    (evidence / "official-starter.ipynb").write_text(json.dumps(notebook, indent=2) + "\n")
    template, judge = None, None
    for cell in notebook["cells"]:
        source = cell["source"]
        source = "".join(source) if isinstance(source, list) else source
        if cell["cell_type"] != "code":
            continue
        if "GRADER_TEMPLATE =" not in source and "JUDGE_MODEL =" not in source:
            continue
        for node in ast.parse(source).body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "JUDGE_MODEL" for t in node.targets):
                judge = ast.literal_eval(node.value)
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "GRADER_TEMPLATE" for t in node.targets):
                assert isinstance(node.value, ast.Call) and node.value.func.attr == "strip"
                template = ast.literal_eval(node.value.func.value).strip()
    assert judge == "gpt-4.1-2025-04-14" and template and "NOT_ATTEMPTED" in template
    (evidence / "official-grader-template.txt").write_text(template)
    rows = list(csv.DictReader(io.StringIO(blobs["simpleqa_verified.csv"].decode("utf-8-sig"))))
    assert len(rows) == 1000
    def rank(row):
        return sha(f"{SEED}:SimpleQA-Verified:{row['original_index']}".encode())
    selected = sorted(rows, key=rank)[:200]
    tasks = []
    for row in selected:
        prompt = row["problem"]
        tasks.append({"id": "SimpleQA-Verified/" + row["original_index"], "domain": "simpleqa", "prompt": prompt, "prompt_sha256": sha(prompt.encode()), "expected_answer": row["answer"], "original_index": int(row["original_index"]), "topic": row["topic"], "answer_type": row["answer_type"]})
    tasks_bytes = (json.dumps(tasks, indent=2, ensure_ascii=False) + "\n").encode()
    (data_dir / "simpleqa200.json").write_bytes(tasks_bytes)
    encoder = tiktoken.encoding_for_model(judge)
    prompt_counts = [len(encoder.encode(template.format(question=t["prompt"], target=t["expected_answer"], predicted_answer=""))) + 16 for t in tasks]
    main_config = json.loads((ROOT / "full-config.json").read_text())
    fields = ["model", "revision", "checkpoint_label", "image", "flavor", "seed", "context_length", "max_tokens", "reasoning_effort"]
    config = {k: main_config[k] for k in fields}
    config.update(scope="approved_knowledge_control", full_run_authorized=False, knowledge_run_authorized=True, output_dir="results/knowledge", config_file="knowledge-config.json", concurrency=32, passes_in_execution_order=[3, 1, 5], share_cache=False, question_count=200, dataset_revision=REVISION, subset_seed=SEED, bootstrap_seed=271828, cap_usd=5, cpu_reserve_usd=2.2, official_grader=judge, grading_transport="OpenAI Batch API", grader_max_completion_tokens=16, worker_hard_deadline_seconds=53*60, provider_timeout_seconds=54*60, local_cancel_after_seconds=55*60, cleanup_reserve_seconds=120)
    (ROOT / "knowledge-config.json").write_text(json.dumps(config, indent=2) + "\n")
    manifest = {"checkpoint_label": config["checkpoint_label"], "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "dataset": DATASET, "dataset_revision": REVISION, "source_sha256": {k: sha(v) for k, v in blobs.items()}, "subset_seed": SEED, "selection": "lowest SHA256(seed:SimpleQA-Verified:original_index), first 200 of 1000", "question_count": 200, "ids": [t["id"] for t in tasks], "tasks_sha256": sha(tasks_bytes), "official_notebook": NOTEBOOK, "notebook_id": notebook_response["metadata"]["id"], "notebook_sha256": sha((evidence / "official-starter.ipynb").read_bytes()), "grader_model": judge, "grader_template_sha256": sha(template.encode()), "question_gold_grader_prompt_tokens": {"min": min(prompt_counts), "max": max(prompt_counts), "mean": sum(prompt_counts)/len(prompt_counts)}, "bare_questions_only": True, "retrieval_or_tools": False, "grading_input": "final answer channel only; visible reasoning is excluded", "grading_cache": "identical full grading prompts share the same official judgment", "grading_transport": "OpenAI Batch API; official rubric and pinned snapshot", "grading_temperature": 0, "raw_judgments_saved": True, "accuracy_definition": "CORRECT / all 200; INCORRECT and NOT_ATTEMPTED are not correct", "planned_paired_test": "exact two-sided McNemar, passes 1 vs 3; paired bootstrap reasoning-token differences", "flatness_rule": "A nonsignificant difference does not establish knowledge equivalence"}
    (data_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"prepared_questions": len(tasks), "planned_outputs": 600, "official_grader": judge, "grader_prompt_tokens_mean": manifest["question_gold_grader_prompt_tokens"]["mean"], "cap_usd": 5, "jobs_created": 0}))


if __name__ == "__main__":
    main()
