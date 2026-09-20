#!/usr/bin/env python3
"""Verify that the US-dollar ceiling now stops the live loop shape per turn."""
import os
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "A2_scaffold"))

import config  # noqa: E402
from agent import run_case  # noqa: E402
from harness import code_check, load_key  # noqa: E402


def main():
    original = config.MAX_COST_USD
    try:
        # First response costs US$0.000432; the second takes the running
        # estimate to US$0.001044, proving the guard fires inside the loop.
        config.MAX_COST_USD = 0.001
        stopped = run_case("CLM-8842", problem="A")
    finally:
        config.MAX_COST_USD = original

    assert stopped["stopped_by"] == "cost_ceiling", stopped
    assert stopped["evidence"] == ["get_claim"], stopped
    assert any(x["guardrail"] == "cost_ceiling"
               for x in stopped["guardrails_fired"]), stopped

    normal = run_case("CLM-8842", problem="A")
    passed, failures = code_check(normal, load_key("A")["CLM-8842"])
    assert normal["stopped_by"] is None, normal
    assert passed, failures
    print("PASS: US$ ceiling fired at US$%.6f before a second tool action." %
          stopped["cost_usd"])
    print("PASS: submitted US$%.3f ceiling leaves CLM-8842 passing." % original)


if __name__ == "__main__":
    main()
