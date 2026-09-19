#!/usr/bin/env python3
"""Liu Zeyuan's isolated D5(b) V1 battery runner.

Uses the same live harness as the shared runner, but fixes the assigned
model to openai/gpt-4o-mini, selects prompt v1 in memory, and writes to a
separate checkpoint file. The repository's shared configuration, runner,
and results are left untouched.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import run_live_battery as base  # noqa: E402

base.config.PROMPT_VERSION = "v1"
# This runner intentionally differs from config.py only in memory. Suppress
# the source-vs-memory warning for that deliberate experiment switch.
base.config._stale_bytecode_warning = lambda: ""
base.ASSIGNED = "openai/gpt-4o-mini"
base.OUT = os.path.join(HERE, "live_results_liu_v1.json")


if __name__ == "__main__":
    raise SystemExit(base.main(sys.argv))
