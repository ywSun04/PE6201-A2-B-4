#!/usr/bin/env python3
"""
D2(a) EVIDENCE · do the three poka-yoke actually fire?

    python3 docs/evidence/verify_pokayoke.py

A poka-yoke that is only described is not a poka-yoke. Each case below
makes the wrong call ON PURPOSE and asserts the tool layer refuses it,
by name. Two of the three reproduce defects Harry recorded as GAP
CONFIRMED in guardrail_checklist.md and reported to this file's owner:

    checklist case 9   check_coverage("99999", ...) returned None silently
    checklist case 12  an unknown tool name escaped as a bare KeyError and
                       took the whole --all run down with it

The third is ours: check_duplicate_claim refusing a claim_id, because
matching on the id finds a resubmission NEVER and does so silently.

Exit code 0 means every wrong call was refused.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "A2_scaffold"))

import config      # noqa: E402
import tools       # noqa: E402

RULE = "=" * 72
results = []


def expect_refusal(label, checklist_ref, expect_type, expect_reason, fn):
    """Call something that must be refused, and report how it was refused."""
    print("  %s" % label)
    print("      %s" % checklist_ref)
    try:
        got = fn()
    except expect_type as err:
        ok = err.reason == expect_reason
        print("      refused : %s.%s" % (type(err).__name__, err.reason))
        print("      says    : %s" % err.detail)
        print("      %s" % ("PASS" if ok else
                            "FAIL - expected reason %r" % expect_reason))
        results.append(ok)
    except Exception as err:                       # noqa: BLE001
        print("      WRONG EXCEPTION TYPE: %s: %s" % (type(err).__name__, err))
        print("      FAIL - this is the bug, not the fix: a type nobody")
        print("             catches ends the whole run, not just this case")
        results.append(False)
    else:
        print("      returned %r and raised nothing" % (got,))
        print("      FAIL - the silent answer is the defect")
        results.append(False)
    print()


def main():
    print()
    print(config.summary())
    print()
    print(RULE)
    print("  POKA-YOKE · every call below is WRONG and must be refused")
    print(RULE)
    print()

    expect_refusal(
        "1 · an invented procedure code",
        "was: guardrail_checklist.md case 9 - returned None, no error",
        tools.UnknownCode, "unknown_procedure_code",
        lambda: tools.check_coverage("99999", "POL-6001"))

    expect_refusal(
        "2 · a policy id that does not exist",
        "same ambiguity: one None meant three different things",
        tools.UnknownPolicy, "unknown_policy_id",
        lambda: tools.check_coverage("45378", "POL-0000"))

    expect_refusal(
        "3 · a tool the agent invented",
        "was: guardrail_checklist.md case 12 - bare KeyError, killed --all",
        tools.UnknownTool, "unknown_tool",
        lambda: tools.call("A", "approve_claim", {"claim_id": "CLM-8842"}))

    expect_refusal(
        "4 · matching a duplicate on the claim id",
        "ours: the silent version of this mistake passes a duplicate",
        tools.UnknownArguments, "claim_id_is_not_a_matching_fact",
        lambda: tools.call("A", "check_duplicate_claim",
                           {"claim_id": "CLM-8933"}))

    expect_refusal(
        "5 · a duplicate check on three of the four facts",
        "ours: the shortcut that wrongly escalates CLM-8850 and CLM-8960",
        tools.UnknownArguments, "incomplete_duplicate_check",
        lambda: tools.call("A", "check_duplicate_claim",
                           {"member_id": "M-5502", "hospital_id": "H-207",
                            "date_of_service": "2026-09-04"}))

    expect_refusal(
        "6 · a real tool called with an argument it does not take",
        "ours: previously an uncaught TypeError, same blast radius as 12",
        tools.UnknownArguments, "bad_arguments",
        lambda: tools.call("A", "get_claim", {"claim": "CLM-8842"}))

    print(RULE)
    print("  ALL FIVE ARE tools.ToolError SUBCLASSES, so agent.py can catch")
    print("  ONE base class and turn each into a single failed record:")
    print()
    print("      except tools.ToolError as err:")
    print("          stopped_by = err.reason")
    print("          record = {\"decision\": \"escalate\",")
    print("                    \"reason\": \"tool layer refused - %s\"")
    print("                              % err.detail}")
    print()
    print("  That clause belongs to Preethi (agent.py). Until it lands these")
    print("  still raise rather than guess, which is the safe half: a crash")
    print("  is recoverable, a confident answer on evidence never gathered")
    print("  is not.")
    print(RULE)
    print("  %d of %d refused correctly" % (sum(results), len(results)))
    print(RULE)
    print()
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
