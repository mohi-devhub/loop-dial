#!/usr/bin/env python3
"""Run exactly the approved full-study cells, without executing generated code."""

import json
import time

import pilot_worker as engine


async def full_study():
    import httpx
    from sglang.srt.hf_transformers import get_tokenizer

    config = engine.CONFIG
    assert config["scope"] == "approved_full_study" and config["full_run_authorized"]
    tokenizer = get_tokenizer(config["model"], tokenizer_revision=config["revision"])
    datasets = {d: json.loads((engine.ROOT / f"data/full/{d}.json").read_text()) for d in ["math", "math-repeat", "gsm8k", "humaneval", "bbh"]}
    warmup = json.loads((engine.ROOT / "data/throughput32.json").read_text())[:1]
    for rows in datasets.values():
        for row in rows:
            if len(tokenizer.encode(row["prompt"])) + config["max_tokens"] + 512 > config["context_length"]:
                raise ValueError(f"Prompt exceeds context: {row['id']}")
    summaries = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10), limits=httpx.Limits(max_connections=40, max_keepalive_connections=40)) as client:
        for case in config["cases"]:
            if engine.DEADLINE - time.monotonic() < 240:
                engine.emit("study_stopped_budget", completed_batches=summaries, next_case=case["key"])
                return
            await engine.start_server(case["passes"], client, case["share_cache"], case["key"])
            records, _ = await engine.batch(client, warmup, case["passes"], 1, 64, f"warmup-{case['key']}", tokenizer, case["share_cache"], case["repeat"])
            if any(r.get("error") for r in records):
                raise RuntimeError("Warmup infrastructure failure")
            for domain in case["domains"]:
                rows = datasets["math-repeat" if domain == "math" and case["repeat"] else domain]
                phase = f"{case['key']}--{domain}"
                engine.PHASE = phase
                await engine.flush(client)
                _, summary = await engine.batch(client, rows, case["passes"], config["concurrency"], config["max_tokens"], phase, tokenizer, case["share_cache"], case["repeat"])
                summaries.append({"case": case["key"], "domain": domain, "passes": case["passes"], "share_cache": case["share_cache"], "repeat": case["repeat"], **summary})
                if summary["errors"]:
                    engine.emit("study_stopped_incomplete", completed_batches=summaries, case=case["key"], domain=domain)
                    return
            engine.emit("case_complete", case=case["key"])
    engine.emit("complete", summaries=summaries, selected_concurrency=config["concurrency"], peak_gpu_memory_mib=max((x["memory_used_mib"] for x in engine.SAMPLES), default=None), total_worker_seconds=time.monotonic() - engine.START)


if __name__ == "__main__":
    engine.study = full_study
    engine.main()
