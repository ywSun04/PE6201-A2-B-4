#!/usr/bin/env python3
"""Verify that the submitted suggest policy holds the irreversible action."""
import os
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "A2_scaffold"))

import config  # noqa: E402
from agent import run_case  # noqa: E402


def main():
    original = config.AUTONOMY
    try:
        config.AUTONOMY = "suggest"
        record = run_case("CLM-8842", problem="A")
    finally:
        config.AUTONOMY = original

    assert record["stopped_by"] == "gate_held", record
    assert "issue_decision_letter" not in record["evidence"], record
    assert any(x["guardrail"] == "gate_held"
               for x in record["guardrails_fired"]), record
    print("PASS: autonomy=suggest held the decision-letter action.")


if __name__ == "__main__":
    main()
