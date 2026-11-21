#!/usr/bin/env python3
"""Fetch pinned original data sources; never downloads model weights."""

import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / "data/source-manifest.json").read_text())
    for source in manifest["sources"]:
        target = ROOT / source["file"]
        target.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(source["url"], timeout=60) as response:
            content = response.read()
        assert hashlib.sha256(content).hexdigest() == source["sha256"], "Pinned source hash mismatch"
        target.write_bytes(content)
        print(str(target.relative_to(ROOT)))


if __name__ == "__main__":
    main()
