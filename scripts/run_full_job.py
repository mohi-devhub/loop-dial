#!/usr/bin/env python3
"""Use the shared guarded job controller for the approved full matrix."""

import os

os.environ["LOOP_DIAL_CONFIG"] = "full-config.json"
from run_pilot_job import main


if __name__ == "__main__":
    raise SystemExit(main())
