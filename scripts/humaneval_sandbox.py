#!/usr/bin/env python3
"""Execute HumanEval candidates only in credential-free network-blocked sandboxes."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
import secrets
import textwrap
import threading
import time

import modal


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/full"
RATE = 0.094716 / 3600
LOCK = threading.Lock()
ACTIVE = {}

SUPERVISOR = r'''
import json,os,resource,subprocess,sys,tempfile
payload=json.loads(sys.argv[1])
program="import random\nrandom.seed(1729)\n"+payload["code"]+"\n"+payload["tests"]+"\ncheck("+payload["entry"]+")\nprint("+repr(payload["seal"])+")\n"
def limits():
 resource.setrlimit(resource.RLIMIT_CPU,(5,6))
 resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
 resource.setrlimit(resource.RLIMIT_FSIZE,(65536,65536))
 resource.setrlimit(resource.RLIMIT_NPROC,(64,64))
with tempfile.TemporaryFile() as stdout,tempfile.TemporaryFile() as stderr:
 try:
  p=subprocess.run([sys.executable,"-I","-c",program],stdout=stdout,stderr=stderr,timeout=10,preexec_fn=limits,env={"PATH":"/usr/local/bin:/usr/bin:/bin"})
  stdout.seek(0);out=stdout.read(65536).decode(errors="replace")
  stderr.seek(0);err=stderr.read(65536).decode(errors="replace")
  print(json.dumps({"correct":p.returncode==0 and out.rstrip().endswith(payload["seal"]),"returncode":p.returncode,"stderr_tail":err[-1200:]}))
 except subprocess.TimeoutExpired:
  print(json.dumps({"correct":False,"failure":"execution_timeout"}))
'''


def extract_code(answer, task):
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", answer, re.S | re.I)
    code = "\n\n".join(blocks).strip() if blocks else answer.strip()
    entry = task["entry_point"]
    if re.search(r"\bdef\s+" + re.escape(entry) + r"\s*\(", code):
        start = task["prompt"].find("def " + entry)
        return task["prompt"][:start] + code
    if code and not code.splitlines()[0].startswith((" ", "\t")):
        code = textwrap.indent(code, "    ")
    return task["prompt"] + code


def completed_cost():
    total = 0
    preflight = OUT / "modal-preflight.json"
    if preflight.exists():
        total += json.loads(preflight.read_text())["cost_upper_usd"]
    ledger = OUT / "modal-ledger.jsonl"
    if ledger.exists():
        total += sum(json.loads(x)["cost_upper_usd"] for x in ledger.read_text().splitlines())
    return total


def allowance():
    state = OUT / "job-state.json"
    if not state.exists():
        return 0.75
    data = json.loads(state.read_text())
    if data["stage"] not in ["COMPLETED", "ERROR", "CANCELED", "CANCELLED"]:
        return 0.75
    return min(2, max(0, 15 - data["conservative_cost_upper_usd"] - 0.05))


def execute_one(app, image, code, task, key, purpose):
    start = time.time()
    with LOCK:
        liability = sum((start - value + 45) * RATE for value in ACTIVE.values()) + 45 * RATE
        if completed_cost() + liability > allowance():
            return {"key": key, "id": task["task_id"], "infrastructure_error": "sandbox_budget_stop"}
        ACTIVE[key] = start
    sb = None
    result = {"key": key, "id": task["task_id"], "purpose": purpose, "code_sha256": hashlib.sha256(code.encode()).hexdigest()}
    try:
        sb = modal.Sandbox.create("sleep", "30", app=app, image=image, block_network=True, cpu=(0.5, 0.5), memory=(1024, 1024), runtime="gvisor", timeout=30, secrets=[], include_oidc_identity_token=False, tags={"project": "loop-dial-full", "purpose": purpose})
        result["sandbox_id"] = sb.object_id
        payload = {"code": code, "tests": task["test"], "entry": task["entry_point"], "seal": "TESTS_PASSED_" + secrets.token_hex(16)}
        proc = sb.exec("python", "-c", SUPERVISOR, json.dumps(payload), timeout=20)
        output = proc.stdout.read()
        error = proc.stderr.read()
        proc.wait()
        if proc.returncode != 0:
            result["infrastructure_error"] = "sandbox_supervisor_failed"
            result["supervisor_stderr"] = error[-1200:]
        else:
            result.update(json.loads(output))
    except Exception as exc:
        result["infrastructure_error"] = type(exc).__name__
    finally:
        if sb is not None:
            try:
                sb.terminate(wait=True)
            except Exception as exc:
                result["termination_error"] = type(exc).__name__
        end = time.time()
        result.update(started_epoch=start, terminated_epoch=end, wall_seconds=end - start, cost_upper_usd=(end - start) * RATE)
        with LOCK:
            ACTIVE.pop(key, None)
            with (OUT / "modal-ledger.jsonl").open("a") as stream:
                stream.write(json.dumps(result) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["gold", "score", "selftest"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--follow", action="store_true", help="Score new saved responses until the inference job terminates")
    args = parser.parse_args()
    tasks = {x["task_id"]: x for x in json.loads((ROOT / "data/full/humaneval-tests.json").read_text())}
    work = []
    if args.mode == "gold":
        for task in tasks.values():
            work.append((task["prompt"] + task["canonical_solution"], task, "gold:" + task["task_id"], "gold-validation"))
    elif args.mode == "selftest":
        task = tasks["HumanEval/0"]
        work = [(task["prompt"] + task["canonical_solution"], task, "selftest:correct", "selftest"), ("def has_close_elements(numbers, threshold):\n    return None", task, "selftest:wrong", "selftest"), ("def has_close_elements(numbers, threshold):\n    while True: pass", task, "selftest:timeout", "selftest")]
    else:
        score_path = OUT / "code-scores.jsonl"
        done = {json.loads(x)["key"] for x in score_path.read_text().splitlines()} if score_path.exists() else set()
        for line in (OUT / "outputs.jsonl").read_text().splitlines():
            record = json.loads(line)
            if record["domain"] != "humaneval" or record.get("error"):
                continue
            key = record["phase"] + ":" + record["id"]
            if key in done:
                continue
            work.append((extract_code(record["answer"], tasks[record["id"]]), tasks[record["id"]], key, "generated-code"))
    if args.limit:
        work = work[:args.limit]
    app = modal.App.lookup("loop-dial-study", create_if_missing=True)
    image = modal.Image.from_registry("python:3.12-slim")
    results = []
    while True:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(execute_one, app, image, *entry) for entry in work]
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                if args.mode == "score":
                    with (OUT / "code-scores.jsonl").open("a") as stream:
                        stream.write(json.dumps(result) + "\n")
                if len(results) % 50 == 0:
                    print(json.dumps({"completed": len(results), "correct": sum(x.get("correct", False) for x in results), "modal_cost_upper_usd": completed_cost()}), flush=True)
        if args.mode != "score" or not args.follow or args.limit:
            break
        done = {json.loads(x)["key"] for x in (OUT / "code-scores.jsonl").read_text().splitlines()}
        content = (OUT / "outputs.jsonl").read_text()
        lines = content.split("\n")[:-1]
        work = []
        for record in map(json.loads, lines):
            key = record["phase"] + ":" + record["id"]
            if record["domain"] == "humaneval" and not record.get("error") and key not in done:
                work.append((extract_code(record["answer"], tasks[record["id"]]), tasks[record["id"]], key, "generated-code"))
        if not work:
            state = json.loads((OUT / "job-state.json").read_text())
            if state["stage"] in ["COMPLETED", "ERROR", "CANCELED", "CANCELLED"]:
                break
            time.sleep(5)
    summary = {"mode": args.mode, "n": len(results), "correct": sum(x.get("correct", False) for x in results), "infrastructure_errors": sum(bool(x.get("infrastructure_error")) for x in results), "modal_cost_upper_usd": completed_cost()}
    if args.mode == "selftest":
        by_key = {x["key"]: x for x in results}
        assert by_key["selftest:correct"]["correct"]
        assert by_key["selftest:wrong"]["correct"] is False
        assert by_key["selftest:timeout"]["correct"] is False
    if args.mode == "gold":
        assert summary["correct"] == len(work) and summary["infrastructure_errors"] == 0, summary
    (OUT / f"sandbox-{args.mode}-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
