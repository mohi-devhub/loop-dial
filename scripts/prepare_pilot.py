#!/usr/bin/env python3
"""Freeze the approved GSM8K pilot and its separate throughput workload."""

import hashlib
import json
from pathlib import Path

from pilot_common import LABEL, PROMPT, rank_id


ROOT = Path(__file__).resolve().parents[1]


def main():
    data = ROOT / "data"
    raw = (data / "gsm8k-test.jsonl").read_bytes()
    rows = [json.loads(line) for line in raw.splitlines()]
    assert len(rows) == 1319
    source = json.loads((data / "gsm8k-source.json").read_text())
    items = []
    for index, row in enumerate(rows):
        stable_id = f"test:{index}"
        prompt = PROMPT.format(row["question"])
        items.append({"id": stable_id, "rank": rank_id(stable_id), "problem": row["question"], "prompt": prompt, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "expected_answer": row["answer"].split("####")[-1].strip()})
    items.sort(key=lambda item: item["rank"])
    (data / "pilot50.json").write_text(json.dumps(items[:50], indent=2) + "\n")
    (data / "throughput32.json").write_text(json.dumps(items[50:82], indent=2) + "\n")
    manifest = {"checkpoint_label": LABEL, "dataset": "GSM8K", "source": source, "source_sha256": hashlib.sha256(raw).hexdigest(), "subset_seed": 20261121, "selection": "ascending SHA256('20261121:GSM8K:test:<row_index>')", "pilot_ids": [x["id"] for x in items[:50]], "throughput_ids": [x["id"] for x in items[50:82]], "future_main300_ids": [x["id"] for x in items[:300]], "prompt_template": PROMPT, "prompt_source": "sgl-eval 0.1.3, vendored NeMo-Skills 645cf567ff08c0ae9cc3fc8e1edbb975b3067816, prompts/math.yaml; zero-shot", "benchmark_max_tokens": 128, "pilot_max_tokens": 8192}
    (data / "subset-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Frozen {len(items[:50])} pilot and {len(items[50:82])} distinct throughput problems for {LABEL}.")


if __name__ == "__main__":
    main()
