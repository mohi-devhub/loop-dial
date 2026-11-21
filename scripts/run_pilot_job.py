#!/usr/bin/env python3
"""Preflight, launch, monitor, and recover an explicitly approved HF study."""

import argparse
import base64
import datetime
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile

from huggingface_hub import HfApi, get_token

from pilot_common import EventDecoder


ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = os.environ.get("LOOP_DIAL_CONFIG", "pilot-config.json")
CONFIG = json.loads((ROOT / CONFIG_FILE).read_text())
OUT = ROOT / CONFIG.get("output_dir", "results/pilot")
STATE = OUT / "job-state.json"
TERMINAL = {"COMPLETED", "ERROR", "CANCELED", "CANCELLED", "DELETED"}


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def liability(unit_price_per_minute, cancel_seconds, cleanup_seconds):
    return math.ceil((cancel_seconds + cleanup_seconds) / 60) * unit_price_per_minute


def stage_of(info):
    return getattr(info.status.stage, "value", info.status.stage)


def preflight():
    OUT.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen("https://huggingface.co/api/jobs/hardware", timeout=20) as response:
        hardware = next(x for x in json.load(response) if x["name"] == CONFIG["flavor"])
    rate = hardware["unitCostUSD"]
    assert hardware["unitLabel"] == "minute"
    assert hardware["accelerator"]["quantity"] == "1"
    bound = liability(rate, CONFIG["local_cancel_after_seconds"], CONFIG["cleanup_reserve_seconds"])
    ledger_path = OUT / "attempt-ledger.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else []
    prior_cost = sum(x["cost_upper_usd"] for x in ledger)
    reserve = CONFIG.get("cpu_reserve_usd", 0)
    if bound + prior_cost + reserve > CONFIG["cap_usd"]:
        raise ValueError("Current price exceeds the approved pilot cap with cleanup reserve")
    if CONFIG["scope"] == "approved_full_study":
        assert CONFIG["full_run_authorized"]
        for domain, count in CONFIG["domain_counts"].items():
            assert len(json.loads((ROOT / f"data/full/{domain}.json").read_text())) == count
        assert len(CONFIG["cases"]) == 12
        assert (OUT / "forecast.json").exists()
        assert json.loads((OUT / "forecast.json").read_text())["selected"]["nominal_total_usd"] <= CONFIG["nominal_threshold_usd"]
    elif CONFIG["scope"] == "approved_knowledge_control":
        assert CONFIG["knowledge_run_authorized"] and CONFIG["cap_usd"] == 5
        assert len(json.loads((ROOT / "data/knowledge/simpleqa200.json").read_text())) == 200
        assert sorted(CONFIG["passes_in_execution_order"]) == [1, 3, 5]
        grader = json.loads((OUT / "grader-preflight.json").read_text())
        assert grader["model_access_verified"] and grader["batch_access_verified"] and grader["model"] == CONFIG["official_grader"]
        assert time.time() - grader["checked_epoch"] < 3600, "Refresh grader access before starting a GPU"
    else:
        pilot = json.loads((ROOT / "data/pilot50.json").read_text())
        benchmark = json.loads((ROOT / "data/throughput32.json").read_text())
        assert len(pilot) == 50 and len(benchmark) == 32
        assert not ({x["id"] for x in pilot} & {x["id"] for x in benchmark})
    result = {"checked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "authenticated": False, "hardware": hardware, "cap_usd": CONFIG["cap_usd"], "cpu_reserve_usd": reserve, "prior_attempts_cost_upper_usd": prior_cost, "planned_liability_with_cleanup_usd": bound + prior_cost + reserve, "full_run_authorized": CONFIG.get("full_run_authorized", False)}
    try:
        user = HfApi().whoami()
        result.update(authenticated=True, namespace=user["name"])
    except Exception as exc:
        result["auth_error_type"] = type(exc).__name__
    save(OUT / "preflight.json", result)
    return result


def bundle():
    if CONFIG["scope"] == "approved_full_study":
        files = [CONFIG_FILE, "scripts/pilot_worker.py", "scripts/pilot_common.py", "scripts/full_worker.py", "data/throughput32.json", "data/full/manifest.json"] + [f"data/full/{d}.json" for d in ["math", "math-repeat", "gsm8k", "humaneval", "bbh"]]
        worker = "full_worker.py"
    elif CONFIG["scope"] == "approved_knowledge_control":
        files = [CONFIG_FILE, "scripts/pilot_worker.py", "scripts/pilot_common.py", "scripts/knowledge_worker.py", "data/knowledge/simpleqa200.json", "data/knowledge/manifest.json"]
        worker = "knowledge_worker.py"
    else:
        files = ["pilot-config.json", "scripts/pilot_worker.py", "scripts/pilot_common.py", "data/pilot50.json", "data/throughput32.json", "data/subset-manifest.json"]
        worker = "pilot_worker.py"
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for name in files:
            zipped.writestr(name, (ROOT / name).read_bytes())
    data = archive.getvalue()
    (OUT / "job-bundle.zip").write_bytes(data)
    encoded = base64.b64encode(data).decode()
    bootstrap = "import base64,io,os,runpy,sys,zipfile; p='/tmp/loop-dial-run'; os.makedirs(p,exist_ok=True); zipfile.ZipFile(io.BytesIO(base64.b64decode(''.join(sys.argv[1:])))).extractall(p); os.chdir(p); sys.path.insert(0,p+'/scripts'); runpy.run_path(p+'/scripts/" + worker + "',run_name='__main__')"
    pieces = [encoded[i:i + 24000] for i in range(0, len(encoded), 24000)]
    return ["python3", "-u", "-c", bootstrap, *pieces], hashlib.sha256(data).hexdigest()


def launch():
    if CONFIG.get("public_archive"):
        raise RuntimeError("Archived configuration: supply your own explicit paid-run authorization before launching")
    result = preflight()
    if not result["authenticated"]:
        print("HF authentication missing. Run hf auth login locally, then retry this authorized pilot. No job was created.")
        return 2
    if STATE.exists():
        raise RuntimeError("A pilot job state already exists. Inspect it before any further paid launch; automatic retries are disabled.")
    command, digest = bundle()
    api = HfApi()
    submitted = time.time()
    intent = {"submitted_epoch": submitted, "namespace": result["namespace"], "rate_usd_per_minute": result["hardware"]["unitCostUSD"], "prior_attempts_cost_upper_usd": result["prior_attempts_cost_upper_usd"], "bundle_sha256": digest, "cap_usd": CONFIG["cap_usd"], "cancel_deadline_epoch": submitted + CONFIG["local_cancel_after_seconds"], "full_run_authorized": CONFIG.get("full_run_authorized", False)}
    save(OUT / "launch-intent.json", intent)
    job = api.run_job(image=CONFIG["image"], command=command, flavor=CONFIG["flavor"], timeout=CONFIG["provider_timeout_seconds"], namespace=result["namespace"], env={"PYTHONUNBUFFERED": "1", "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1", "LOOP_DIAL_SCOPE": CONFIG["scope"], "LOOP_DIAL_CONFIG": CONFIG_FILE})
    state = {**intent, "job_id": job.id, "url": job.url, "stage": stage_of(job), "history": []}
    save(STATE, state)
    with (OUT / "monitor.log").open("a") as log:
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "monitor"], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    state["monitor_pid"] = process.pid
    save(STATE, state)
    print(json.dumps({"job_id": job.id, "url": job.url, "monitor_pid": process.pid, "cap_usd": CONFIG["cap_usd"]}))
    return 0


def collect_logs(api, state):
    secret = get_token()
    seen = set()
    decoder = EventDecoder()
    events_path = OUT / "events.jsonl"
    if events_path.exists():
        for line in events_path.read_text().splitlines():
            event = json.loads(line)
            seen.add(hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest())
    for line in api.fetch_job_logs(job_id=state["job_id"], namespace=state["namespace"]):
        clean = line.replace(secret, "[REDACTED]") if secret else line
        with (OUT / "job.log").open("a") as stream:
            stream.write(clean + "\n")
        try:
            event = decoder.feed(clean)
        except Exception as exc:
            with (OUT / "recovery-errors.jsonl").open("a") as stream:
                stream.write(json.dumps({"error_type": type(exc).__name__, "line_sha256": hashlib.sha256(clean.encode()).hexdigest()}) + "\n")
            continue
        if event is None:
            continue
        fingerprint = hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        with events_path.open("a") as stream:
            stream.write(json.dumps(event) + "\n")
        if event["kind"] == "request":
            record = event["record"]
            if CONFIG["scope"] in ["approved_full_study", "approved_knowledge_control"]:
                name = "warmup-outputs.jsonl" if record["phase"].startswith("warmup-") else "outputs.jsonl"
            else:
                name = "outputs.jsonl" if record["phase"].startswith("pilot-pass") else "throughput-outputs.jsonl"
            with (OUT / name).open("a") as stream:
                stream.write(json.dumps(record) + "\n")
        elif event["kind"] == "complete":
            save(OUT / "summary.json", event)
        elif event["kind"] == "sweep_complete":
            save(OUT / "throughput-summary.json", event)


def monitor():
    state = json.loads(STATE.read_text())
    api = HfApi()
    log_thread = threading.Thread(target=collect_logs, args=(api, state), daemon=True)
    log_thread.start()
    last_stage = None
    cancel_sent = False
    while True:
        now = time.time()
        try:
            info = api.inspect_job(job_id=state["job_id"], namespace=state["namespace"])
            stage = stage_of(info)
        except Exception as exc:
            stage = "INSPECTION_ERROR"
            print(json.dumps({"error_type": type(exc).__name__}), flush=True)
        if stage != last_stage:
            state["history"].append({"epoch": now, "stage": stage})
            print(json.dumps({"stage": stage, "elapsed_seconds": now - state["submitted_epoch"]}), flush=True)
            last_stage = stage
        state.update(stage=stage, last_observed_epoch=now, conservative_cost_upper_usd=state.get("prior_attempts_cost_upper_usd", 0) + math.ceil((now - state["submitted_epoch"]) / 60) * state["rate_usd_per_minute"])
        save(STATE, state)
        if stage in TERMINAL:
            log_thread.join(timeout=5)
            state["terminal_observed_epoch"] = now
            save(STATE, state)
            return
        if not log_thread.is_alive():
            log_thread = threading.Thread(target=collect_logs, args=(api, state), daemon=True)
            log_thread.start()
        if now >= state["cancel_deadline_epoch"]:
            try:
                api.cancel_job(job_id=state["job_id"], namespace=state["namespace"])
                if not cancel_sent:
                    state["cancel_requested_epoch"] = now
                cancel_sent = True
                print("Pilot deadline reached; cancellation requested.", flush=True)
            except Exception as exc:
                print(json.dumps({"cancel_error_type": type(exc).__name__}), flush=True)
        time.sleep(5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["preflight", "launch", "monitor"])
    args = parser.parse_args()
    if args.action == "preflight":
        result = preflight()
        print(json.dumps(result, indent=2))
        return 0 if result["authenticated"] else 2
    if args.action == "launch":
        return launch()
    monitor()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
