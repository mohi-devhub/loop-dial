"""Pure selection, scoring, statistics, and event encoding for the pilot."""

import base64
from decimal import Decimal, InvalidOperation
import gzip
import hashlib
import json
import math
import re
import statistics


LABEL = "thinkingmachines/TML-d24-varloop-research (varloop research checkpoint)"
PROMPT = "Solve the following math problem. Make sure to put the answer (and only answer) inside \\boxed{{}}.\n\n{}"
EVENT_PREFIX = "LOOP_DIAL "
PART_PREFIX = "LOOP_DIAL_PART "


def rank_id(stable_id, seed=20261121):
    return hashlib.sha256(f"{seed}:GSM8K:{stable_id}".encode()).hexdigest()


def boxed_answer(text):
    start = text.rfind("\\boxed{")
    if start < 0:
        return None
    start += len("\\boxed{")
    depth = 1
    for i in range(start, len(text)):
        depth += (text[i] == "{") - (text[i] == "}")
        if depth == 0:
            return text[start:i]
    return None


def number(text):
    text = text.replace(",", "").strip().replace("−", "-")
    fraction = re.fullmatch(r"\\(?:d?frac)\{(-?[\d.]+)\}\{(-?[\d.]+)\}", text)
    try:
        if fraction:
            return Decimal(fraction[1]) / Decimal(fraction[2])
        if re.fullmatch(r"-?[\d.]+/-?[\d.]+", text):
            a, b = text.split("/")
            return Decimal(a) / Decimal(b)
        value = Decimal(text.strip("$ "))
        return value if value.is_finite() else None
    except (InvalidOperation, ZeroDivisionError):
        return None


def score(answer, expected, finish_reason):
    extracted = boxed_answer(answer)
    method = "last_boxed"
    if extracted is None:
        matches = re.findall(r"[-−]?(?:\d[\d,]*\.?\d*|\.\d+)(?:[eE][+-]?\d+)?", answer)
        extracted = matches[-1] if matches else ""
        method = "last_number_in_final_answer"
    prediction = number(extracted)
    correct = finish_reason != "length" and prediction is not None and prediction == number(str(expected))
    return {"correct": correct, "extracted_answer": extracted, "extraction_method": method, "truncated": finish_reason == "length"}


def wilson(correct, count):
    if not count:
        return [None, None]
    p, z = correct / count, 1.959963984540054
    den = 1 + z * z / count
    center = (p + z * z / (2 * count)) / den
    half = z * math.sqrt(p * (1 - p) / count + z * z / (4 * count * count)) / den
    return [max(0, center - half), min(1, center + half)]


def aggregate(records, seconds):
    good = [r for r in records if not r.get("error")]
    tokens = sum(r["completion_tokens"] for r in good)
    right = sum(r.get("correct", False) for r in records)
    scored = any("correct" in r for r in records)
    result = {"checkpoint_label": LABEL, "attempted": len(records), "successful_requests": len(good), "errors": len(records) - len(good), "correct": right, "accuracy": right / len(records) if records else None, "wilson_95": wilson(right, len(records)), "total_completion_tokens": tokens, "wall_seconds": seconds, "aggregate_tokens_per_second": tokens / seconds if seconds > 0 else None, "truncations": sum(r.get("truncated", False) for r in records)}
    for name in ["reasoning_tokens", "answer_tokens", "completion_tokens", "request_wall_seconds", "effective_decode_seconds_per_token"]:
        values = [r[name] for r in good if r.get(name) is not None]
        result[f"mean_{name}"] = statistics.mean(values) if values else None
        result[f"median_{name}"] = statistics.median(values) if values else None
    result["tokens_per_correct_answer"] = tokens / right if right else None
    if not scored:
        result.update(correct=None, accuracy=None, wilson_95=[None, None])
    return result


def encode_event(event):
    body = json.dumps({"checkpoint_label": LABEL, **event}, separators=(",", ":"), ensure_ascii=False).encode()
    return EVENT_PREFIX + base64.b64encode(gzip.compress(body)).decode()


def decode_event(line):
    position = line.find(EVENT_PREFIX)
    if position < 0:
        return None
    return json.loads(gzip.decompress(base64.b64decode(line[position + len(EVENT_PREFIX):].strip())))


def event_lines(event):
    encoded = encode_event(event)
    if len(encoded) <= 16000:
        return [encoded]
    payload = encoded[len(EVENT_PREFIX):]
    pieces = [payload[i:i + 12000] for i in range(0, len(payload), 12000)]
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return [PART_PREFIX + json.dumps({"id": digest, "index": index, "total": len(pieces), "data": piece}) for index, piece in enumerate(pieces)]


class EventDecoder:
    def __init__(self):
        self.pending = {}

    def feed(self, line):
        position = line.find(PART_PREFIX)
        if position < 0:
            return decode_event(line)
        part = json.loads(line[position + len(PART_PREFIX):])
        pieces = self.pending.setdefault(part["id"], {})
        pieces[part["index"]] = part["data"]
        if len(pieces) != part["total"]:
            return None
        payload = "".join(pieces[i] for i in range(part["total"]))
        del self.pending[part["id"]]
        if hashlib.sha256(payload.encode()).hexdigest() != part["id"]:
            raise ValueError("Corrupt event transport")
        return decode_event(EVENT_PREFIX + payload)
