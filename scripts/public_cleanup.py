"""Remove workstation and account presentation details from public documents."""

from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def main():
    for path in [ROOT / "results/full/budget-report.json"]:
        if path.exists():
            value = json.loads(path.read_text())
            value.pop("opening_hf_credit_usd_user_reported", None)
            path.write_text(json.dumps(value, indent=2) + "\n")
    for path in ROOT.glob("*.md"):
        text = path.read_text()
        text = re.sub(r"/Users/[^\s)\"<>]+", "<local-path-omitted>", text)
        text = text.replace("The existing Superset browser launcher points to a missing desktop app, and a plain HTTP page fetch is not an authenticated billing receipt. ", "")
        text = text.replace("The starting HF credit balance is user-reported at $24.40; no closing balance has been supplied.", "Account balances and billing identifiers are omitted from this public export.")
        text = re.sub(r"(?m)^\|[^\n]*(?:[Oo]pening|credit balance)[^\n]*\|\n", "", text)
        text = re.sub(r"https://huggingface.co/jobs/[^\s)]+", "https://huggingface.co/docs/hub/jobs", text)
        text = text.replace("[HF job](https://huggingface.co/docs/hub/jobs)", "HF Jobs run (account identifier withheld)")
        text = re.sub(r"(?<!thinkingmachines/)TML-d24-varloop-research", "thinkingmachines/TML-d24-varloop-research", text)
        text = text.replace("results/full/scored-outputs.jsonl)", "results/full/scored-outputs.jsonl.gz)")
        text = text.replace("results/full/outputs.jsonl)", "results/full/scored-outputs.jsonl.gz)")
        text = text.replace("results/pilot/rescored-numeric-v2.jsonl)", "results/pilot/rescored-numeric-v2.jsonl.gz)")
        path.write_text(text)


if __name__ == "__main__":
    main()
