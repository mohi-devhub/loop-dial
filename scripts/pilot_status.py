#!/usr/bin/env python3
"""Print a compact view of recovered pilot events without generated text."""

from collections import Counter
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / os.environ.get("LOOP_DIAL_CONFIG", "pilot-config.json")).read_text())
OUT = ROOT / CONFIG.get("output_dir", "results/pilot")


def main():
    state = json.loads((OUT / "job-state.json").read_text())
    events = []
    path = OUT / "events.jsonl"
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    requests = [e["record"] for e in events if e["kind"] == "request"]
    print(json.dumps({"job_id": state["job_id"], "stage": state["stage"], "cost_upper_usd": state.get("conservative_cost_upper_usd"), "request_counts": dict(Counter(r["phase"] for r in requests)), "request_errors": sum(bool(r.get("error")) for r in requests)}))
    batches = [e for e in events if e["kind"] == "batch"]
    for e in batches[-3:]:
        print(json.dumps({"phase": e["phase"], "passes": e["passes"], "concurrency": e["concurrency"], "seconds": e["summary"]["wall_seconds"], "tokens_per_second": e["summary"]["aggregate_tokens_per_second"], "correct": e["summary"]["correct"], "errors": e["summary"]["errors"], "gpu": e["gpu"]}))
    samples = [e for e in events if e["kind"] == "gpu_samples"]
    if samples:
        print(json.dumps({"latest_gpu_sample": samples[-1]["samples"][-1]}))
    progress = [e for e in events if e["kind"] in ["server_ready", "server_failed", "failed", "sweep_complete", "complete", "server_progress"]]
    if progress:
        e = progress[-1]
        if e["kind"] == "server_progress":
            lines = [x for x in e["log_tail"].splitlines() if len(x) < 1500]
            print(json.dumps({"kind": e["kind"], "phase": e["phase"], "log_tail": lines[-12:]}))
        else:
            print(json.dumps({k: v for k, v in e.items() if k not in ["info", "summaries", "log_tail"]}))


if __name__ == "__main__":
    main()
