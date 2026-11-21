#!/usr/bin/env python3
"""Use the guarded controller for the approved $5 knowledge control."""

import os

os.environ["LOOP_DIAL_CONFIG"] = "knowledge-config.json"
from run_pilot_job import main


if __name__ == "__main__":
    raise SystemExit(main())
