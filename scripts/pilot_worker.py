#!/usr/bin/env python3
"""Run only the approved pilot, inside the pinned SGLang GPU image."""

import asyncio
import contextlib
import json
import os
from pathlib import Path
import signal
import statistics
import subprocess
import sys
import threading
import time

from pilot_common import LABEL, aggregate, boxed_answer, event_lines, score


ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / os.environ.get("LOOP_DIAL_CONFIG", "pilot-config.json")).read_text())
OUT = ROOT / CONFIG.get("output_dir", "results/pilot")
START = time.monotonic()
DEADLINE = START + CONFIG["worker_hard_deadline_seconds"]
SERVER = None
LOCK = threading.Lock()
SAMPLES = []
PHASE = "startup"
STOP = threading.Event()
BASE = "http://127.0.0.1:30000"
CURRENT_LOG = None


def emit(kind, **data):
    event = {"kind": kind, "worker_elapsed_seconds": time.monotonic() - START, **data}
    with LOCK:
        with (OUT / "events.jsonl").open("a") as stream:
            stream.write(json.dumps({"checkpoint_label": LABEL, **event}) + "\n")
            stream.flush()
        for line in event_lines(event):
            print(line, flush=True)


def stop_server():
    global SERVER
    process, SERVER = SERVER, None
    if process is None or process.poll() is not None:
        return
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)


def hard_deadline():
    if not STOP.wait(max(0, DEADLINE - time.monotonic())):
        emit("deadline", reason="worker hard deadline")
        stop_server()
        os._exit(124)


def sample_gpu():
    while not STOP.is_set():
        try:
            result = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu,utilization.memory,power.draw", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5, check=True)
            values = [float(x.strip()) for x in result.stdout.strip().split(",")]
            item = {"elapsed_seconds": time.monotonic() - START, "phase": PHASE, "memory_used_mib": values[0], "memory_total_mib": values[1], "gpu_util_percent": values[2], "memory_util_percent": values[3], "power_watts": values[4]}
            SAMPLES.append(item)
            with (OUT / "gpu-samples.jsonl").open("a") as stream:
                stream.write(json.dumps(item) + "\n")
            if len(SAMPLES) % 60 == 0:
                emit("gpu_samples", samples=SAMPLES[-60:])
                if PHASE.startswith("load-") and CURRENT_LOG is not None and CURRENT_LOG.exists():
                    emit("server_progress", phase=PHASE, log_tail=CURRENT_LOG.read_text(errors="replace")[-8000:])
        except Exception as exc:
            emit("gpu_sample_error", error_type=type(exc).__name__)
        STOP.wait(0.5)


def gpu_stats(since):
    samples = [x for x in SAMPLES if x["elapsed_seconds"] >= since]
    return {"sample_count": len(samples), "peak_gpu_memory_mib": max((x["memory_used_mib"] for x in samples), default=None), "mean_gpu_util_percent": statistics.mean(x["gpu_util_percent"] for x in samples) if samples else None, "mean_memory_util_percent": statistics.mean(x["memory_util_percent"] for x in samples) if samples else None}


async def flush(client):
    response = await client.post(BASE + "/flush_cache")
    response.raise_for_status()


async def start_server(passes, client, share_cache=False, case_key=None):
    global SERVER, PHASE, CURRENT_LOG
    stop_server()
    PHASE = f"load-{case_key or ('pass' + str(passes))}"
    args = [sys.executable, "-m", "sglang.launch_server", "--model-path", CONFIG["model"], "--revision", CONFIG["revision"], "--tp", "1", "--ep", "1", "--attention-backend", "fa4", "--dtype", "bfloat16", "--page-size", "128", "--grammar-backend", "xgrammar", "--reasoning-parser", "inkling", "--tool-call-parser", "inkling2", "--inkling2-loop-num-passes", str(passes), "--context-length", str(CONFIG["context_length"]), "--max-running-requests", "32", "--cuda-graph-max-bs-decode", "32", "--mem-fraction-static", "0.80", "--random-seed", str(CONFIG["seed"]), "--host", "127.0.0.1", "--port", "30000"]
    if share_cache:
        args.append("--inkling2-loop-share-cache")
    emit("server_start", passes=passes, share_cache=share_cache, case_key=case_key, command=args)
    env = dict(os.environ)
    env.pop("HF_TOKEN", None)
    env["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
    CURRENT_LOG = OUT / f"server-{case_key or ('pass' + str(passes))}.log"
    log = CURRENT_LOG.open("w")
    SERVER = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
    log.close()
    started = time.monotonic()
    while time.monotonic() < min(DEADLINE - 180, started + 900):
        if SERVER.poll() is not None:
            tail = CURRENT_LOG.read_text(errors="replace")[-16000:]
            emit("server_failed", passes=passes, exit_code=SERVER.returncode, log_tail=tail)
            raise RuntimeError("SGLang exited before readiness")
        try:
            response = await client.get(BASE + "/health", timeout=5)
            if response.status_code == 200:
                info = await client.get(BASE + "/get_server_info", timeout=15)
                emit("server_ready", passes=passes, share_cache=share_cache, case_key=case_key, startup_seconds=time.monotonic() - started, info=info.json() if info.status_code == 200 else None)
                return
        except Exception:
            pass
        await asyncio.sleep(2)
    raise TimeoutError("Server startup exhausted its time allowance")


async def request_one(client, semaphore, item, passes, max_tokens, phase, tokenizer, share_cache=False, repeat_index=0):
    submitted = time.monotonic()
    async with semaphore:
        sent = time.monotonic()
        record = {"checkpoint_label": LABEL, "model": CONFIG["model"], "revision": CONFIG["revision"], "id": item["id"], "domain": item.get("domain", "gsm8k"), "level": item.get("level"), "task": item.get("task"), "passes": passes, "share_cache": share_cache, "repeat": repeat_index, "phase": phase, "prompt_sha256": item["prompt_sha256"], "prompt": item["prompt"], "expected_answer": item["expected_answer"], "max_tokens": max_tokens, "seed": CONFIG["seed"], "reasoning_effort": CONFIG["reasoning_effort"], "training_regime": "RL training depth" if passes == 3 else "beyond the trained range" if passes > 5 else "midtraining range, not RL'd"}
        reasoning, answer, event_times = [], [], []
        try:
            if DEADLINE - sent < 150:
                raise TimeoutError("Not enough pilot budget time to admit another request")
            payload = {"model": CONFIG["model"], "messages": [{"role": "user", "content": item["prompt"]}], "temperature": 0, "top_p": 1, "seed": CONFIG["seed"], "max_tokens": max_tokens, "reasoning_effort": CONFIG["reasoning_effort"], "stream": True, "stream_options": {"include_usage": True}}
            usage, finish, done = None, None, False
            async with client.stream("POST", BASE + "/v1/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if time.monotonic() > DEADLINE - 90:
                        raise TimeoutError("Pilot deadline during response")
                    if not line.startswith("data: "):
                        continue
                    if line[6:] == "[DONE]":
                        done = True
                        break
                    chunk = json.loads(line[6:])
                    if "error" in chunk:
                        raise RuntimeError("Server returned a streaming error")
                    if chunk.get("usage"):
                        usage = chunk["usage"]
                    for choice in chunk.get("choices", []):
                        delta = choice.get("delta", {})
                        r, a = delta.get("reasoning_content") or "", delta.get("content") or ""
                        if r or a:
                            event_times.append(time.monotonic() - sent)
                        reasoning.append(r)
                        answer.append(a)
                        finish = choice.get("finish_reason") or finish
            ended = time.monotonic()
            if not done or not finish or not usage or usage.get("completion_tokens", 0) <= 0:
                raise RuntimeError("Incomplete stream or missing generated-token usage")
            reasoning, answer = "".join(reasoning), "".join(answer)
            if not reasoning and not answer:
                raise RuntimeError("Empty generated output")
            count = usage["completion_tokens"]
            record.update(reasoning=reasoning, answer=answer, finish_reason=finish, usage=usage, completion_tokens=count, prompt_tokens=usage.get("prompt_tokens"), local_queue_seconds=sent - submitted, request_wall_seconds=ended - sent, end_to_end_seconds=ended - submitted, first_text_seconds=event_times[0] if event_times else None, text_event_seconds=event_times, effective_decode_seconds_per_token=(event_times[-1] - event_times[0]) / (count - 1) if len(event_times) > 1 and count > 1 else None)
            if tokenizer is not None:
                record["reasoning_tokens"] = len(tokenizer.encode(reasoning, add_special_tokens=False))
                record["answer_tokens"] = len(tokenizer.encode(answer, add_special_tokens=False))
                record["token_count_remainder"] = count - record["reasoning_tokens"] - record["answer_tokens"]
                record["split_token_method"] = "checkpoint tokenizer, each parsed channel encoded independently; remainder retained"
                if CONFIG["scope"] == "approved_pilot_only":
                    record.update(score(answer, item["expected_answer"], finish))
                else:
                    record["truncated"] = finish == "length"
        except Exception as exc:
            record.update(error=type(exc).__name__, request_wall_seconds=time.monotonic() - sent)
            record.setdefault("reasoning", "".join(reasoning) if isinstance(reasoning, list) else reasoning)
            record.setdefault("answer", "".join(answer) if isinstance(answer, list) else answer)
            if hasattr(exc, "response"):
                record["http_status"] = exc.response.status_code
        emit("request", record=record)
        return record


async def batch(client, items, passes, concurrency, max_tokens, phase, tokenizer=None, share_cache=False, repeat_index=0):
    semaphore = asyncio.Semaphore(concurrency)
    started = time.monotonic()
    records = await asyncio.gather(*(request_one(client, semaphore, item, passes, max_tokens, phase, tokenizer, share_cache, repeat_index) for item in items))
    seconds = time.monotonic() - started
    summary = aggregate(records, seconds)
    emit("batch", passes=passes, phase=phase, share_cache=share_cache, repeat=repeat_index, concurrency=concurrency, summary=summary, gpu=gpu_stats(started - START), load_average=os.getloadavg())
    return records, summary


async def study():
    global PHASE
    import httpx
    from sglang.srt.hf_transformers import get_tokenizer

    tokenizer = get_tokenizer(CONFIG["model"], tokenizer_revision=CONFIG["revision"])
    pilot = json.loads((ROOT / "data/pilot50.json").read_text())
    bench = json.loads((ROOT / "data/throughput32.json").read_text())
    assert len(pilot) == 50 and len(bench) == 32
    assert not ({x["id"] for x in pilot} & {x["id"] for x in bench})
    for item in pilot + bench:
        if len(tokenizer.encode(item["prompt"])) + CONFIG["max_tokens"] + 512 > CONFIG["context_length"]:
            raise ValueError("Prompt exceeds context budget")
    limits = httpx.Limits(max_connections=40, max_keepalive_connections=40)
    async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10), limits=limits) as client:
        await start_server(3, client)
        warm, _ = await batch(client, bench[:4], 3, 4, 64, "warmup", tokenizer)
        if any(x.get("error") for x in warm) or not any(x.get("reasoning") for x in warm):
            raise RuntimeError("Warmup failed or official reasoning parser returned no reasoning")
        measurements = {c: [] for c in CONFIG["sweep_concurrencies"]}
        for round_index, order in enumerate(CONFIG["sweep_orders"]):
            for concurrency in order:
                if DEADLINE - time.monotonic() < 600:
                    raise TimeoutError("Insufficient time for approved sweep and scored runs")
                PHASE = f"sweep-c{concurrency}-r{round_index}"
                await flush(client)
                _, summary = await batch(client, bench, 3, concurrency, CONFIG["sweep_max_tokens"], PHASE)
                measurements[concurrency].append(summary)
        choices = []
        for concurrency, runs in measurements.items():
            speeds = [x["aggregate_tokens_per_second"] for x in runs]
            cv = statistics.stdev(speeds) / statistics.mean(speeds)
            stable = all(x["errors"] == 0 and x["successful_requests"] == 32 for x in runs) and cv <= CONFIG["sweep_max_cv"]
            choices.append({"concurrency": concurrency, "stable": stable, "cv": cv, "median_tokens_per_second": statistics.median(speeds), "min_tokens_per_second": min(speeds), "max_tokens_per_second": max(speeds), "repeats": len(runs)})
        stable_choices = [x for x in choices if x["stable"]]
        if not stable_choices:
            emit("sweep_failed", choices=choices)
            raise RuntimeError("No stable error-free concurrency level")
        chosen = max(stable_choices, key=lambda x: x["median_tokens_per_second"])["concurrency"]
        emit("sweep_complete", choices=choices, selected_concurrency=chosen)
        summaries = []
        for passes in CONFIG["passes_in_execution_order"]:
            if passes != 3:
                await start_server(passes, client)
                warm, _ = await batch(client, bench[:1], passes, 1, 64, "warmup", tokenizer)
                if any(x.get("error") for x in warm):
                    raise RuntimeError("Pass-count warmup failed")
            PHASE = f"pilot-pass{passes}"
            await flush(client)
            _, summary = await batch(client, pilot, passes, chosen, CONFIG["max_tokens"], PHASE, tokenizer)
            summaries.append({"passes": passes, **summary})
            if summary["errors"]:
                raise RuntimeError("Scored batch has infrastructure errors; stopping without retries")
        emit("complete", summaries=summaries, selected_concurrency=chosen, peak_gpu_memory_mib=max((x["memory_used_mib"] for x in SAMPLES), default=None), total_worker_seconds=time.monotonic() - START)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=hard_deadline, daemon=True).start()
    result = subprocess.run(["nvidia-smi", "--query-gpu=name,uuid,memory.total,driver_version", "--format=csv,noheader,nounits"], capture_output=True, text=True, check=True, timeout=15)
    gpu_lines = result.stdout.strip().splitlines()
    if len(gpu_lines) != 1 or "RTX PRO 6000" not in gpu_lines[0]:
        raise RuntimeError("Allocated GPU differs from the approved single RTX PRO 6000")
    emit("environment", gpu=gpu_lines, python=sys.version, cpu_count=os.cpu_count(), load_average=os.getloadavg(), config=CONFIG)
    threading.Thread(target=sample_gpu, daemon=True).start()
    try:
        help_result = subprocess.run([sys.executable, "-m", "sglang.launch_server", "--help"], capture_output=True, text=True, timeout=120)
        for flag in ["--inkling2-loop-num-passes", "--reasoning-parser", "--cuda-graph-max-bs-decode"]:
            if flag not in help_result.stdout:
                raise RuntimeError(f"Pinned image does not advertise {flag}")
        asyncio.run(study())
    except Exception as exc:
        emit("failed", error_type=type(exc).__name__, message=str(exc), gpu=gpu_stats(0))
        raise
    finally:
        stop_server()
        STOP.set()
        emit("worker_stopped", elapsed_seconds=time.monotonic() - START)


if __name__ == "__main__":
    main()
