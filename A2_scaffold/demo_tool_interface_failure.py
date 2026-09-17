#!/usr/bin/env python3
"""
PE6201 · A2 · D7 FAILURE 2 - the tool interface, not loop control again
====================================================================
    python3 demo_tool_interface_failure.py

Same method as demo_loop_failure.py, different layer. D7 requires this
second failure to sit in the TOOL INTERFACE or the PROMPT - here it is
the interface: tools.lookup_policy().

THE FIX ALREADY LIVES IN tools.py, SO THIS FILE DEMONSTRATES ITS ABSENCE.
lookup_policy() computes and returns `remaining` (annual_limit minus
used_to_date) instead of handing back the raw policy row and trusting
whoever reads it to do the subtraction correctly. Its own docstring
names the trap: "Testing against the limit is a silent wrong answer on
any policy with spend on it." This script deletes that computed field -
"the working tool, minus X" - and shows a script that was never taught
to look for `remaining` reads `annual_limit` instead, and wrongly
approves a claim that should have escalated.

CLM-9302 (Harry's case): three lines - 250 + 90 + 400 = 740 - each
individually small, together over the 600 actually remaining on
POL-4102 (annual_limit 6000, used_to_date 5400). 740 < 6000, so reading
the raw limit gives a confident, wrong "approve". 740 > 600, so the
fixed tool's `remaining` gives the right "escalate".

Everything below runs on the SCRIPTED backend. D7 needs no API key.
====================================================================
"""
import tools
from agent import run_case
import backends
import config


def _lookup_policy_without_remaining(member_id):
    """The deletion. Same two lookups tools.lookup_policy makes - reimplemented
    here (not calling tools.lookup_policy itself, which by the time this runs
    IS this function, monkeypatched in) - just never does the subtraction.
    This is tools.py BEFORE the fix; not a hypothetical."""
    m = next((x for x in tools._load("A", "members")
              if x["member_id"] == member_id), None)
    if m is None:
        return None
    p = next((x for x in tools._load("A", "policies")
              if x["policy_id"] == m["policy_id"]), None)
    if p is None:
        return None
    return {"member": m, "policy": p}
    # no "remaining" key - exactly what a caller had before the fix


# A script for an agent that was never taught to look for `remaining` -
# only `annual_limit` is compared, because that is the only limit-shaped
# field in the (deleted) tool's answer. It never reads used_to_date
# either: nothing in the record it was handed asks it to.
NAIVE_SCRIPT = [
    {"thought": "Fetch the claim first.",
     "calls": [("get_claim", {"claim_id": "CLM-9302"})]},

    {"thought": "Check the policy limit and price every line - the tool "
                "gave me annual_limit, so that is what I compare against.",
     "calls": [("lookup_policy", {"member_id": "M-3390"}),
               ("check_coverage", {"code": "99213", "policy_id": "POL-4102"}),
               ("check_coverage", {"code": "80053", "policy_id": "POL-4102"}),
               ("check_coverage", {"code": "45378", "policy_id": "POL-4102"}),
               ("lookup_hospital", {"hospital_id": "H-207"})]},

    {"thought": "Total 740, all three lines covered, 740 is well under "
                "the 6000 annual_limit. Approve.",
     "calls": [("issue_decision_letter", {
         "claim_id": "CLM-9302", "decision": "approve_in_principle",
         "lines_resolved": 3, "approved_total": 740, "refused_total": 0})]},

    {"final": {
        "decision": "approve_in_principle",
        "reason": "3 lines, 250+90+400=740, all covered, 740 < annual_limit "
                  "6000. approved_total 740.",
     },
     "thought": "Confident, and wrong: 740 is under the LIMIT but over the "
                "600 actually REMAINING - a fact this tool never returned."},
]


def main():
    print()
    print(config.summary())
    print("  demonstrating on CLM-9302 (Problem A)")
    print()

    # ---- BEFORE: the working tool, remaining computed -----------------
    before = run_case("CLM-9302", problem="A")
    print("BEFORE - the fixed tool (lookup_policy returns `remaining`)")
    print("  decision=%s  trigger=%s" % (before["decision"], before.get("trigger")))
    print("  reason: %s" % before["reason"][:100])

    # ---- AFTER: the same claim, MINUS the `remaining` field -----------
    real_lookup = tools.lookup_policy
    tools.lookup_policy = _lookup_policy_without_remaining   # <- the deletion
    backends.SCRIPTS["CLM-9302-naive"] = NAIVE_SCRIPT
    try:
        after = run_case("CLM-9302-naive", problem="A")
    finally:
        tools.lookup_policy = real_lookup                    # <- put it back
        del backends.SCRIPTS["CLM-9302-naive"]

    print()
    print("AFTER - the tool MINUS `remaining`; the agent reads annual_limit")
    print("  decision=%s  stopped_by=%s" % (after["decision"], after["stopped_by"]))
    print("  reason: %s" % after["reason"][:100])

    print()
    print("=" * 68)
    print("  1 · THE INSTRUMENTATION THAT FOUND IT")
    print("      NOT the guardrail layer. check_evidence recomputes per-line")
    print("      coverage and totals from tools.py, and every line here IS")
    print("      genuinely covered - 740 is the correct SUM of covered")
    print("      lines. The guard has no concept of 'annual limit' at all;")
    print("      that rule lives upstream of it, in lookup_policy. So this")
    print("      failure is invisible to every D3(a) guard, and only shows")
    print("      up as a WRONG DECISION against the D4 answer key.")
    print("  2 · WHERE THE FIX BELONGS, AND WHY THE OTHER TWO ARE WRONG")
    print("      TOOL INTERFACE (the actual fix): lookup_policy computes")
    print("      `remaining` once, in one place. Every future caller - this")
    print("      script, a live model, next year's rewrite - gets the right")
    print("      number for free.")
    print("      LOOP CONTROL would be the wrong layer: nothing about this")
    print("      failure is a turn-count or duplicate-call problem. Adding")
    print("      a guardrail could not have caught it - the run is short,")
    print("      clean, and every guard above passes it.")
    print("      PROMPT would be the wrong layer too: a sentence telling")
    print("      the model 'remember to subtract used_to_date' is paid on")
    print("      every call, of every run, forever, and silently stops")
    print("      working the day the prompt is trimmed or the model changes.")
    print("      An interface constraint is paid once and holds - D2(b)'s")
    print("      argument, reappearing here as the reason D7's fix belongs")
    print("      where it does.")
    print("  3 · BEFORE AND AFTER")
    print("      before: %-20s  after: %s" % (before["decision"], after["decision"]))
    print("      Restoring `remaining` (removing the monkeypatch) is what")
    print("      recovers the correct behaviour - nothing else changed.")
    print("  4 · A LIMIT ON THIS FIX, FOUND WHILE WRITING IT UP")
    print("      lookup_policy's `policy` sub-dict still exposes the raw")
    print("      annual_limit and used_to_date fields ALONGSIDE `remaining`")
    print("      - it adds the safe number, it does not remove the unsafe")
    print("      one. A caller that reaches for annual_limit anyway (as")
    print("      NAIVE_SCRIPT deliberately does) can still make this")
    print("      mistake even with the current fix in place. A stricter")
    print("      poka-yoke would return ONLY `remaining` for this decision,")
    print("      the same move D2(b) calls a closed Literal: making the")
    print("      wrong read impossible, not just unnecessary.")
    print("=" * 68)
    print()


if __name__ == "__main__":
    main()
