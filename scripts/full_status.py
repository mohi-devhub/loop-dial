#!/usr/bin/env python3
"""Print the full-study progress and spending bound without generated text."""

import json
from pathlib import Path
import time


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/full"


def main():
    state = json.loads((OUT / "job-state.json").read_text())
    progress_path = OUT / "numeric-progress.json"
    progress = json.loads(progress_path.read_text()) if progress_path.exists() else {}
    print(json.dumps({"stage": state["stage"], "gpu_cost_upper_usd": state.get("conservative_cost_upper_usd"), "elapsed_minutes": ((state.get("terminal_observed_epoch") or time.time()) - state["submitted_epoch"]) / 60, "raw_outputs": progress.get("raw_outputs_processed", 0), "latest_phase": progress.get("last_phase"), "latest_phase_count": progress.get("counts", {}).get(progress.get("last_phase"))}))
    events_path = OUT / "events.jsonl"
    if events_path.exists() and not progress:
        events = []
        for line in events_path.read_text().splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        useful = [x for x in events if x["kind"] in ["server_progress", "server_ready", "failed"]]
        if useful:
            e = useful[-1]
            print(json.dumps({"kind": e["kind"], "elapsed_seconds": e["worker_elapsed_seconds"], "phase": e.get("phase"), "passes": e.get("passes"), "log_tail": [l for l in e.get("log_tail", "").splitlines() if len(l) < 1000][-5:]}))


if __name__ == "__main__":
    main()
