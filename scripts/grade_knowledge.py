#!/usr/bin/env python3
"""Use the official SimpleQA Verified rubric and GPT-4.1 snapshot via Batch."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

from openai import OpenAI
import tiktoken


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/knowledge"
MODEL = "gpt-4.1-2025-04-14"
TERMINAL = {"completed", "failed", "expired", "cancelled"}


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def client():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        for line in (ROOT / ".env").read_text().splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" in line and line.split("=", 1)[0].strip() == "OPENAI_API_KEY":
                key = line.split("=", 1)[1].strip().strip("\"'")
    if not key:
        raise ValueError("OPENAI_API_KEY is unavailable")
    return OpenAI(api_key=key, max_retries=0, timeout=60)


def official_prompt(task, answer, template):
    return template.format(question=task["prompt"], target=task["expected_answer"], predicted_answer=answer)


def parse_grade(content):
    letter = content.strip()
    if letter not in {"A", "B", "C"}:
        raise ValueError("Official grader did not return a single A/B/C letter")
    return {"grade_letter": letter, "grade_str": {"A": "CORRECT", "B": "INCORRECT", "C": "NOT_ATTEMPTED"}[letter], "correct": letter == "A"}


def prepare():
    config = json.loads((ROOT / "knowledge-config.json").read_text())
    manifest = json.loads((ROOT / "data/knowledge/manifest.json").read_text())
    tasks_path = ROOT / "data/knowledge/simpleqa200.json"
    assert hashlib.sha256(tasks_path.read_bytes()).hexdigest() == manifest["tasks_sha256"]
    tasks = {t["id"]: t for t in json.loads(tasks_path.read_text())}
    rows = read_jsonl(OUT / "outputs.jsonl")
    assert len(rows) == 600 and not any(r.get("error") for r in rows)
    keys = {(r["passes"], r["id"]) for r in rows}
    assert keys == {(p, i) for p in [1, 3, 5] for i in tasks}, "Incomplete or duplicated control matrix"
    template = (ROOT / "evidence/knowledge/official-grader-template.txt").read_text()
    assert hashlib.sha256(template.encode()).hexdigest() == manifest["grader_template_sha256"]
    state = json.loads((OUT / "job-state.json").read_text())
    assert state["stage"] in {"COMPLETED", "CANCELED", "CANCELLED", "ERROR"} and state.get("terminal_observed_epoch")
    gpu_upper = math.ceil((state["terminal_observed_epoch"] - state["submitted_epoch"]) / 60) * state["rate_usd_per_minute"]
    encoder = tiktoken.encoding_for_model(MODEL)
    requests, mapping = {}, {}
    for row in rows:
        task = tasks[row["id"]]
        assert row["model"] == config["model"] and row["revision"] == config["revision"]
        assert row["prompt_sha256"] == task["prompt_sha256"] and not row["share_cache"]
        prompt = official_prompt(task, row["answer"], template)
        identity = "sqv-" + hashlib.sha256(prompt.encode()).hexdigest()
        mapping[f"{row['phase']}:{row['id']}"] = identity
        requests[identity] = {"custom_id": identity, "method": "POST", "url": "/v1/chat/completions", "body": {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_completion_tokens": config["grader_max_completion_tokens"]}}
    input_upper = sum(len(encoder.encode(r["body"]["messages"][0]["content"])) + 16 for r in requests.values())
    output_upper = len(requests) * config["grader_max_completion_tokens"]
    grader_upper = (input_upper * 1 + output_upper * 4) / 1e6 * 1.05 + 0.01
    assert grader_upper <= config["cpu_reserve_usd"], "Official grading exceeds its reserved allowance"
    assert gpu_upper + grader_upper <= config["cap_usd"], "Combined generation and grading would exceed $5"
    request_text = "".join(json.dumps(r) + "\n" for r in requests.values())
    request_path = OUT / "grader-requests.jsonl"
    if (OUT / "grader-launch-intent.json").exists():
        assert request_path.read_text() == request_text, "Never mutate submitted grading requests"
    request_path.write_text(request_text)
    save(OUT / "grader-map.json", mapping)
    budget = {"cap_usd": 5, "gpu_timestamp_upper_usd": gpu_upper, "grader_model": MODEL, "original_outputs": 600, "unique_grading_prompts": len(requests), "reused_identical_prompt_judgments": 600 - len(requests), "input_tokens_upper": input_upper, "output_tokens_upper": output_upper, "batch_price_input_usd_per_million": 1, "batch_price_output_usd_per_million": 4, "price_source": "https://developers.openai.com/api/docs/guides/batch", "grader_cost_upper_usd": grader_upper, "combined_cost_upper_usd": gpu_upper + grader_upper, "request_file_sha256": hashlib.sha256(request_text.encode()).hexdigest(), "grading_input": "Final answer only; reasoning excluded", "unparseable_grades": "Fail and report; never silently score invalid grader responses"}
    save(OUT / "grading-budget.json", budget)
    print(json.dumps(budget))


def submit():
    prepare()
    assert not (OUT / "grader-launch-intent.json").exists(), "A grading submission was already attempted; inspect its state before retrying"
    budget = json.loads((OUT / "grading-budget.json").read_text())
    api = client()
    with (OUT / "grader-requests.jsonl").open("rb") as source:
        uploaded = api.files.create(file=source, purpose="batch")
    save(OUT / "grader-launch-intent.json", {"submitted_epoch": time.time(), "input_file_id": uploaded.id, "request_sha256": budget["request_file_sha256"], "combined_cost_upper_usd": budget["combined_cost_upper_usd"], "cap_usd": 5})
    batch = api.batches.create(input_file_id=uploaded.id, endpoint="/v1/chat/completions", completion_window="24h", metadata={"experiment": "loop-dial-simpleqa-verified-200", "request_sha256": budget["request_file_sha256"]})
    save(OUT / "grader-batch-state.json", batch.model_dump(mode="json"))
    print(json.dumps({"batch_id": batch.id, "status": batch.status, "unique_judgments": budget["unique_grading_prompts"], "combined_cost_upper_usd": budget["combined_cost_upper_usd"]}))


def collect(api, batch):
    if batch.output_file_id:
        content = api.files.content(batch.output_file_id).content
        (OUT / "grader-output.jsonl").write_bytes(content)
    if batch.error_file_id:
        content = api.files.content(batch.error_file_id).content
        (OUT / "grader-errors.jsonl").write_bytes(content)
    if batch.status != "completed":
        raise RuntimeError("Official grading batch did not complete")
    judgments = read_jsonl(OUT / "grader-output.jsonl")
    expected = {r["custom_id"] for r in read_jsonl(OUT / "grader-requests.jsonl")}
    assert len(judgments) == len(expected) and {r["custom_id"] for r in judgments} == expected
    grades, usage_in, usage_out = {}, 0, 0
    for result in judgments:
        assert not result.get("error") and result["response"]["status_code"] == 200
        body = result["response"]["body"]
        assert body["model"] == MODEL
        assert body["choices"][0]["finish_reason"] == "stop"
        grade = parse_grade(body["choices"][0]["message"]["content"])
        grades[result["custom_id"]] = {**grade, "grader_model": body["model"], "grader_custom_id": result["custom_id"], "grader_usage": body["usage"], "grader_version": "official-simpleqa-verified-gpt-4.1-2025-04-14"}
        usage_in += body["usage"]["prompt_tokens"]
        usage_out += body["usage"]["completion_tokens"]
    mapping = json.loads((OUT / "grader-map.json").read_text())
    rows = read_jsonl(OUT / "outputs.jsonl")
    scored = [{**row, **grades[mapping[f"{row['phase']}:{row['id']}"]]} for row in rows]
    (OUT / "scored-outputs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in scored))
    budget = json.loads((OUT / "grading-budget.json").read_text())
    grader_usage_cost = (usage_in + usage_out * 4) / 1e6
    assert grader_usage_cost <= budget["grader_cost_upper_usd"]
    save(OUT / "budget-report.json", {**budget, "grader_prompt_tokens": usage_in, "grader_completion_tokens": usage_out, "grader_usage_cost_upper_usd": grader_usage_cost, "combined_resource_cost_upper_usd": budget["gpu_timestamp_upper_usd"] + grader_usage_cost, "invoice_verified": False, "grading_requests_completed": len(grades), "scored_outputs": len(scored)})
    print(json.dumps({"scored_outputs": len(scored), "unique_official_judgments": len(grades), "grader_usage_cost_upper_usd": grader_usage_cost, "combined_resource_cost_upper_usd": budget["gpu_timestamp_upper_usd"] + grader_usage_cost}))


def watch(once=False):
    state = json.loads((OUT / "grader-batch-state.json").read_text())
    api = client()
    previous = None
    while True:
        batch = api.batches.retrieve(state["id"])
        save(OUT / "grader-batch-state.json", batch.model_dump(mode="json"))
        progress = {"batch_id": batch.id, "status": batch.status, "counts": batch.request_counts.model_dump() if batch.request_counts else None}
        if progress != previous:
            print(json.dumps(progress), flush=True)
            previous = progress
        if batch.status in TERMINAL:
            collect(api, batch)
            return
        if once:
            return
        time.sleep(20)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "submit", "watch", "status"])
    action = parser.parse_args().action
    if action == "prepare":
        prepare()
    elif action == "submit":
        submit()
    else:
        watch(once=action == "status")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__, "status_code": getattr(exc, "status_code", None), "action_stopped": True}), file=sys.stderr)
        raise SystemExit(1)
