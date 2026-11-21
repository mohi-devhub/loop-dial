"""Math grading with exact numeric normalization and bounded symbolic fallback."""

import re
import signal
from contextlib import contextmanager

import sympy as sp
from latex2sympy2_extended import NormalizationConfig, normalize_latex
from math_verify import LatexExtractionConfig, parse, verify

from pilot_common import boxed_answer


VERSION = "loop-dial-math-equivalence-v2"
CONSTANT_WORDS = {"pi", "infty", "infinity", "sin", "cos", "tan", "log", "ln", "exp", "sqrt", "oo"}


@contextmanager
def time_limit(seconds=3):
    def expired(*_):
        raise TimeoutError("symbolic grader time limit")
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def extract_final(answer):
    result = boxed_answer(answer)
    if result is not None:
        return result.strip()
    lines = [x.strip() for x in answer.strip().splitlines() if x.strip()]
    result = lines[-1] if lines else ""
    return re.sub(r"^(?:the\s+)?(?:final\s+)?answer\s*(?:is|:)\s*", "", result, flags=re.I).strip()


def normalize(text, domain="math"):
    text = str(text).strip().replace("−", "-").replace("×", r"\times").replace("π", r"\pi")
    for currency in [r"\$", "$", "€", "£", "₹", "¥"]:
        text = text.replace(currency, "")
    for char, fraction in {"½": r"\frac{1}{2}", "¼": r"\frac{1}{4}", "¾": r"\frac{3}{4}"}.items():
        text = text.replace(char, fraction)
    text = re.sub(r"(?<=\d)(?:\^\{(?:st|nd|rd|th)\}|\^(?:st|nd|rd|th)|(?:st|nd|rd|th)\b|\\textsuperscript\{(?:st|nd|rd|th)\})", "", text, flags=re.I)
    unit = re.search(r"\\(?:text|mathrm|textrm)\{\s*([A-Za-z][A-Za-z \-]*)\}\s*(?:\^\{?-?\d+\}?)?\s*$", text)
    if unit and text[:unit.start()].strip():
        text = text[:unit.start()].strip()
    suffix = re.search(r"\s+([A-Za-z]{2,}(?:[ \-]+[A-Za-z]{2,})*)\.?\s*$", text)
    if suffix and re.search(r"[\d\\+*/^(){}]", text[:suffix.start()]) and not (set(suffix[1].lower().split()) & CONSTANT_WORDS):
        text = text[:suffix.start()].strip()
    text = text.replace(r"\%", "").replace("%", "")
    text = normalize_latex(text, NormalizationConfig(units=True, boxed="none", malformed_operators=True))
    text = text.strip().rstrip(".").replace(r"\,", "").replace(r"\!", "")
    if re.fullmatch(r"[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", text):
        text = text.replace(",", "")
    return text


def rational(text):
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text):
        return sp.Rational(text)
    if re.fullmatch(r"[+-]?\d+\s*/\s*[+-]?\d+", text):
        a, b = text.split("/")
        return sp.Rational(int(a), int(b))
    return None


def equivalent(expected, predicted, domain="math"):
    if not predicted or len(predicted) > 2000:
        return False, "empty_or_oversized"
    if any(x in predicted.lower() for x in ["__import__", "exec(", "eval(", "open("]):
        return False, "invalid_expression"
    gold, pred = normalize(expected, domain), normalize(predicted, domain)
    if "=" not in gold and re.fullmatch(r"[A-Za-z]\s*=\s*[^=]+", pred):
        pred = pred.split("=", 1)[1].strip()
    if gold.replace(" ", "") == pred.replace(" ", ""):
        return True, "normalized_equal"
    a, b = rational(gold), rational(pred)
    if a is not None and b is not None:
        if a == b:
            return True, "exact_rational"
        if "%" in str(expected) and a / 100 == b:
            return True, "percent_fraction_equivalent"
        if "%" in predicted and abs(a) <= 1 and a == b / 100:
            return True, "percent_fraction_equivalent"
        return False, "exact_rational"
    with time_limit():
        left = parse("$" + gold + "$", [LatexExtractionConfig()])
        right = parse("$" + pred + "$", [LatexExtractionConfig()])
        if not left or not right:
            return False, "unparsed"
        if isinstance(left[0], sp.Expr) and isinstance(right[0], sp.Expr):
            if sp.simplify(left[0] - right[0]) == 0:
                return True, "sympy_equivalent"
        return bool(verify(left, right)), "symbolic_verify"


def grade_math(answer, expected, domain="math", finish_reason="stop"):
    extracted = extract_final(answer)
    result = {"grader_version": VERSION, "extracted_answer": extracted, "raw_string_match": extracted == str(expected).strip(), "truncated": finish_reason == "length"}
    if finish_reason == "length":
        return {**result, "correct": False, "equivalence_method": "truncated"}
    try:
        correct, method = equivalent(str(expected), extracted, domain)
        return {**result, "correct": correct, "equivalence_method": method}
    except Exception as exc:
        return {**result, "correct": None, "grader_error": type(exc).__name__}
