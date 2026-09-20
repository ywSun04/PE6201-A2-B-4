#!/usr/bin/env python3
"""D2(c): reproducible grouped-versus-sequential scripted control.

This compares every scripted Problem A path twice.  The grouped arm uses
the committed script.  The sequential control preserves the same calls in
the same order and only splits each multi-call turn into one call per turn.
It therefore tests scheduling rather than a different decision policy.

The scripted backend's token figures are deterministic transcript estimates,
not vendor-reported live tokens.  They are labelled as estimates everywhere
this script writes them.
"""
import copy
import json
import os
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "A2_scaffold"))

import agent  # noqa: E402
import config  # noqa: E402
from backends import SCRIPTS  # noqa: E402
from harness import code_check, load_cases, load_key  # noqa: E402


OUT = os.path.join(HERE, "parallel_call_measurement.json")


def sequentialise(script):
    """Split each grouped call list without changing call order or finals."""
    out = []
    for move in script:
        if "final" in move:
            out.append(copy.deepcopy(move))
            continue
        calls = move.get("calls") or [(move["tool"], move["args"])]
        for name, args in calls:
            out.append({"thought": move.get("thought", ""),
                        "calls": [(name, copy.deepcopy(args))]})
    return out


def run_arm(case_id, schedule, expected):
    original = SCRIPTS[case_id]
    try:
        SCRIPTS[case_id] = schedule
        record = agent.run_case(case_id, problem="A")
    finally:
        SCRIPTS[case_id] = original
    passed, failures = code_check(record, expected)
    return record, passed, failures


def totals(rows):
    return {
        "cases": len(rows),
        "tool_calls": sum(len(row["record"]["evidence"]) for row in rows),
        "turns": sum(row["record"]["turns"] for row in rows),
        "input_token_estimate": sum(row["record"]["tokens_in"] for row in rows),
        "output_token_estimate": sum(row["record"]["tokens_out"] for row in rows),
        "cost_estimate_usd": round(sum(row["record"]["cost_usd"] for row in rows), 6),
        "code_check_passes": sum(row["passed"] for row in rows),
    }


def main():
    key = load_key("A")
    case_ids = [cid for cid in load_cases("A") if cid in SCRIPTS]
    grouped, sequential, comparisons = [], [], []

    # This is a scheduling control, so its arms must not differ because the
    # longer transcript reaches a protective cap first. The submitted caps
    # are checked elsewhere; this control isolates only call scheduling.
    original_limits = (config.MAX_TURNS, config.MAX_TOKENS_PER_RUN,
                       config.MAX_COST_USD)
    try:
        config.MAX_TURNS = 1000
        config.MAX_TOKENS_PER_RUN = 10 ** 9
        config.MAX_COST_USD = None
        for case_id in case_ids:
            base = copy.deepcopy(SCRIPTS[case_id])
            grouped_record, grouped_passed, grouped_failures = run_arm(
                case_id, base, key[case_id])
            sequential_record, sequential_passed, sequential_failures = run_arm(
                case_id, sequentialise(base), key[case_id])
            grouped.append({"case_id": case_id, "record": grouped_record,
                            "passed": grouped_passed, "failures": grouped_failures})
            sequential.append({"case_id": case_id, "record": sequential_record,
                               "passed": sequential_passed, "failures": sequential_failures})
            comparisons.append({
                "case_id": case_id,
                "same_decision": grouped_record["decision"] == sequential_record["decision"],
                "same_evidence_order": grouped_record["evidence"] == sequential_record["evidence"],
                "grouped_code_check": grouped_passed,
                "sequential_code_check": sequential_passed,
            })
    finally:
        (config.MAX_TURNS, config.MAX_TOKENS_PER_RUN,
         config.MAX_COST_USD) = original_limits

    result = {
        "method": (
            "Offline scripted control. Grouped schedules are the committed "
            "Problem A scripts; sequential schedules split only independent "
            "calls into one call per turn. Token values are scripted transcript "
            "estimates, not live vendor measurements."
        ),
        "case_ids": case_ids,
        "grouped": totals(grouped),
        "sequential": totals(sequential),
        "comparison": {
            "same_decision_cases": sum(x["same_decision"] for x in comparisons),
            "same_evidence_order_cases": sum(x["same_evidence_order"] for x in comparisons),
            "all_code_checks_pass": all(x["grouped_code_check"] and x["sequential_code_check"]
                                        for x in comparisons),
        },
        "per_case": comparisons,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)

    print("D2(c) grouped-versus-sequential scripted control")
    for name in ("sequential", "grouped"):
        arm = result[name]
        print("%-10s cases=%d calls=%d turns=%d input_est=%d output_est=%d "
              "cost_est=US$%.6f code_checks=%d/%d" % (
                  name, arm["cases"], arm["tool_calls"], arm["turns"],
                  arm["input_token_estimate"], arm["output_token_estimate"],
                  arm["cost_estimate_usd"], arm["code_check_passes"], arm["cases"]))
    print("same decisions=%d/%d; same evidence order=%d/%d; all code checks=%s" % (
        result["comparison"]["same_decision_cases"], len(case_ids),
        result["comparison"]["same_evidence_order_cases"], len(case_ids),
        result["comparison"]["all_code_checks_pass"]))
    print("Wrote %s" % OUT)


if __name__ == "__main__":
    main()
