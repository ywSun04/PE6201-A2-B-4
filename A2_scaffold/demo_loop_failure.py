#!/usr/bin/env python3
"""
PE6201 · A2 scaffold — D7 WORKED EXAMPLE: the loop failure
====================================================================
    python3 demo_loop_failure.py

This is the shape D7 asks for, done once so you can copy the method.

D7 requires each failure to be built as a DELETION FROM YOUR WORKING
AGENT - "the working agent, minus X" - not as a separately written bad
agent. Putting X back must recover the behaviour. That is what makes it
a diagnosis rather than a story.

Here X is ACTION DE-DUPLICATION. Everything else is untouched.

WHAT YOU SHOULD NOTICE: with the guard deleted the run does not crash.
No exception. No error. It repeats a call it already made, burns turns
and tokens - AND STILL RETURNS THE RIGHT ANSWER. A pass-rate table
would show it as a clean pass. Neither the step cap nor the budget
ceiling fires, because neither is breached: they bound the damage, they
do not detect the fault.

You only ever see this IF YOU ARE COUNTING. That is why instrumentation
is a requirement and not a nicety, and it is the whole lesson of D7.

Everything below runs on the SCRIPTED backend, so it costs nothing and
reproduces exactly. D7 needs no API key.
====================================================================
"""
import copy
import statistics

import backends
import config
import harness
from agent import run_case
from guardrails import Guardrails

# Works for either problem. The default follows config.PROBLEM.
CASES = {"B": "REF-5602", "A": "CLM-8842"}

# Every Problem A case that currently has a script in backends.py. This is a
# PRELIMINARY set (7 cases: the shipped CLM-8842 + Harry's 6), not the full
# 30-50 case D4 evaluation set - most of the team's cases have no script yet.
# Re-run this once the whole team's cases are scripted; nothing below changes
# except the numbers.
SCRIPTED_PROBLEM_A = ["CLM-8842", "CLM-9301", "CLM-9302", "CLM-9303",
                     "CLM-9304", "CLM-9305", "CLM-9306"]


def turn_distribution(label, case_ids=None, problem="A"):
    """D7 point 2: the turn distribution across the (currently scripted)
    evaluation set - median, worst case, and how many runs hit the step
    cap. ONE number is not a distribution, which is why this is separate
    from the single-case before/after demo below."""
    case_ids = case_ids or SCRIPTED_PROBLEM_A
    results, _ = harness.run_set(case_ids=case_ids, problem=problem)
    turns = [r["record"]["turns"] for r in results]
    hit_cap = sum(1 for r in results if r["record"]["stopped_by"] == "step_cap")
    passed = sum(1 for r in results if r["passed"])
    print("  %s - n=%d trials over %d cases" % (label, len(results), len(case_ids)))
    print("    median turns        %s" % statistics.median(turns))
    print("    worst case turns    %s" % max(turns))
    print("    hit the step cap    %d of %d" % (hit_cap, len(results)))
    print("    pass rate           %d/%d (%.0f%%)"
          % (passed, len(results), 100.0 * passed / len(results)))
    return {"turns": turns, "hit_cap": hit_cap, "passed": passed,
            "total": len(results)}


def _dedup_disabled(self, tool, args):
    """The deletion. Only the DUPLICATE CHECK is gone - never raises, whatever
    is called and however many times. Recording what was called (calls_log)
    is separate bookkeeping the evidence check also reads (D3b cases 1-3, 10);
    it is not de-duplication's to own, so removing de-dup must not blind it.

    FOUND WHILE BUILDING THIS DEMO: the first version of this deletion
    replaced check_duplicate wholesale (`lambda self, tool, args: None`),
    which also stopped calls_log from being written - since that recording
    lived INSIDE check_duplicate. That produced a false result: the looping
    run failed the evidence check for reasons that had nothing to do with
    de-duplication, and the intended "still gets the right answer, just
    burns more" story was never actually observed. Fixed by keeping the
    recording and deleting only the check-and-raise behaviour - the precise
    thing D7 calls "the guard", no more and no less.
    """
    self.calls_log.append((tool, dict(args)))


def _looping_script(CASE):
    """The working script, with one call repeated - a model that has
    forgotten it already asked. This is the observable behaviour; the
    deletion below is what lets it continue."""
    steps = copy.deepcopy(backends.SCRIPTS[CASE])
    repeat = copy.deepcopy(steps[1])          # ask the same thing again
    repeat["thought"] = "Let me check the criteria again to be sure."
    return steps[:2] + [repeat, repeat] + steps[2:]


def main(case=None, problem=None):
    problem = problem or config.PROBLEM
    CASE = case or CASES[problem]

    print()
    print(config.summary())
    print("  demonstrating on %s (Problem %s)" % (CASE, problem))
    print()

    print("=" * 68)
    print("  D7 POINT 2 · TURN DISTRIBUTION, GUARD INTACT (baseline)")
    print("=" * 68)
    baseline = turn_distribution("baseline (all guards intact)")
    print()

    original = backends.SCRIPTS[CASE]

    # ---- BEFORE: the working agent ----------------------------------
    before = run_case(CASE, problem=problem)
    print("BEFORE - the working agent, guard in place")
    print("  turns %d · tool calls %d · tokens %d · cost US$%.5f · decision %s"
          % (before["turns"], len(before["evidence"]),
             before["tokens_in"] + before["tokens_out"],
             before["cost_usd"], before["decision"]))

    # ---- AFTER: the same agent, MINUS the de-duplication guard ------
    backends.SCRIPTS[CASE] = _looping_script(CASE)
    real_check = Guardrails.check_duplicate
    Guardrails.check_duplicate = _dedup_disabled   # <- the deletion (see below)
    try:
        after = run_case(CASE, problem=problem)
    finally:
        Guardrails.check_duplicate = real_check                  # <- put it back
        backends.SCRIPTS[CASE] = original

    print()
    print("AFTER - the working agent MINUS action de-duplication")
    print("  turns %d · tool calls %d · tokens %d · cost US$%.5f · decision %s"
          % (after["turns"], len(after["evidence"]),
             after["tokens_in"] + after["tokens_out"],
             after["cost_usd"], after["decision"]))
    print("  stopped by: %s" % after["stopped_by"])

    # ---- the four things D7 asks you to report ----------------------
    spend = (after["tokens_in"] + after["tokens_out"]) / \
            max(1, before["tokens_in"] + before["tokens_out"])
    print()
    print("=" * 68)
    print("  1 · THE INSTRUMENTATION THAT FOUND IT")
    print("      turns and cost logged per run. NOTHING RAISED AN EXCEPTION.")
    print("      The run cost %.1fx more and still answered %r"
          % (spend, after["decision"]))
    if after["decision"] == before["decision"]:
        print("      - THE SAME ANSWER AS THE WORKING AGENT. A pass-rate table")
        print("      alone would show this run as a clean pass. It is only")
        print("      visible because turns and cost were counted.")
    print("  2 · THE TURN DISTRIBUTION")
    print("      before: %d turns   after: %d turns   cap: %d"
          % (before["turns"], after["turns"], config.MAX_TURNS))
    print("      runs that hit the cap: %d of 2"
          % sum(1 for r in (before, after) if r["stopped_by"] == "step_cap"))
    print("  3 · THE FIX, AND WHY THE OTHER TWO LAYERS WERE WRONG")
    print("      Action de-duplication caught it, in the CODE layer.")
    # Say what ACTUALLY happened, not what sounds right. On this data the
    # other two guards did not fire at all - which is the stronger lesson.
    if after["stopped_by"] != "step_cap":
        print("      The STEP CAP never fired: the loop finished at %d turns,"
              % after["turns"])
        print("      inside the cap of %d. A cap bounds the damage; it does not"
              % config.MAX_TURNS)
        print("      detect this. Raise the repeat count and it would - later,")
        print("      and still without naming the cause.")
    else:
        print("      The step cap DID stop it, at %d turns - later than the"
              % after["turns"])
        print("      de-duplication guard, and without naming the cause.")
    print("      The BUDGET CEILING never fired either: %d tokens against a"
          % (after["tokens_in"] + after["tokens_out"]))
    print("      ceiling of %d." % config.MAX_TOKENS_PER_RUN)
    print("      A PROMPT fix cannot be relied on - the model is the thing")
    print("      that forgot. Only the code layer remembers.")
    print("  4 · BEFORE AND AFTER, ON THE WHOLE SET - not just this one case")
    print("=" * 68)
    print()
    print("=" * 68)
    print("  D7 POINT 4 (continued) · WHOLE-SET PASS RATE, DEDUP REMOVED")
    print("=" * 68)
    real_check = Guardrails.check_duplicate
    Guardrails.check_duplicate = _dedup_disabled   # <- the deletion, set-wide
    try:
        after_set = turn_distribution("guard removed, legitimate scripts unchanged")
    finally:
        Guardrails.check_duplicate = real_check                  # <- put it back
    print()
    if after_set["passed"] == baseline["passed"] == after_set["total"]:
        print("  Pass rate held at %d/%d with the guard removed. Expected: none of"
              % (after_set["passed"], after_set["total"]))
        print("  these 7 scripts repeat a call on their own, so de-dup was never")
        print("  the thing keeping them correct - it only matters for a run that")
        print("  ALREADY tends to circle, which is exactly what %s demonstrates "
              "above." % CASE)
    else:
        print("  Pass rate moved: baseline %d/%d -> guard removed %d/%d. Investigate"
              % (baseline["passed"], baseline["total"],
                 after_set["passed"], after_set["total"]))
        print("  which case changed before concluding anything about the cap.")
    print()
    print("  CAVEAT: these 7 cases are what has a script today - Harry's 6 plus")
    print("  the shipped CLM-8842. Re-run this file once the team's full 30-50")
    print("  case set is scripted; the method above does not change, the")
    print("  numbers will.")
    print("=" * 68)
    print()
    print("  Now do this for YOUR second failure, in the TOOL INTERFACE or")
    print("  the PROMPT - not loop control again. State which layer the fix")
    print("  belongs in and why the other two were the wrong place. That")
    print("  judgement is most of the mark.")
    print()


if __name__ == "__main__":
    main()
