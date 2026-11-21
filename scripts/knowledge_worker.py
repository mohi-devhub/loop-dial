#!/usr/bin/env python3
"""Generate the approved SimpleQA control inside the pinned GPU image."""

import json
import time

import pilot_worker as engine


async def knowledge_study():
    import httpx
    from sglang.srt.hf_transformers import get_tokenizer

    config = engine.CONFIG
    assert config["scope"] == "approved_knowledge_control" and config["knowledge_run_authorized"]
    assert config["cap_usd"] == 5 and sorted(config["passes_in_execution_order"]) == [1, 3, 5]
    tasks = json.loads((engine.ROOT / "data/knowledge/simpleqa200.json").read_text())
    assert len(tasks) == 200 and len({t["id"] for t in tasks}) == 200
    tokenizer = get_tokenizer(config["model"], tokenizer_revision=config["revision"])
    assert all(len(tokenizer.encode(t["prompt"])) + config["max_tokens"] + 512 <= config["context_length"] for t in tasks)
    summaries = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10), limits=httpx.Limits(max_connections=40, max_keepalive_connections=40)) as client:
        for passes in config["passes_in_execution_order"]:
            if engine.DEADLINE - time.monotonic() < 240:
                engine.emit("study_stopped_budget", summaries=summaries, next_pass=passes)
                return
            case = f"knowledge-p{passes}"
            await engine.start_server(passes, client, False, case)
            warm, _ = await engine.batch(client, tasks[:1], passes, 1, 64, f"warmup-{case}", tokenizer)
            if any(r.get("error") for r in warm):
                raise RuntimeError("Warmup failed")
            engine.PHASE = case + "--simpleqa"
            await engine.flush(client)
            _, summary = await engine.batch(client, tasks, passes, config["concurrency"], config["max_tokens"], engine.PHASE, tokenizer)
            summaries.append({"passes": passes, **summary})
            if summary["errors"]:
                engine.emit("study_stopped_incomplete", summaries=summaries)
                return
    engine.emit("complete", summaries=summaries, peak_gpu_memory_mib=max((x["memory_used_mib"] for x in engine.SAMPLES), default=None), total_worker_seconds=time.monotonic() - engine.START)


if __name__ == "__main__":
    engine.study = knowledge_study
    engine.main()
