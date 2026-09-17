#!/usr/bin/env python3
"""
D2(a) EVIDENCE · the three questions, answered from the data.

    python3 docs/evidence/score_tool_set.py

The brief is specific about what a good answer to question 1 looks like:
"Name the task that fails. Start from the minimum set and add on an
OBSERVED failure, never an imagined one."

So this counts. For each tool it reports how many cases in the current
set turn on the fact only that tool returns, and names them. A tool that
no case turns on has not earned its place, whatever it sounds like it is
for.

Question 3 - what it costs when never called - is also measured rather
than asserted: each descriptor is rendered with the real formatter and
counted, because that block is re-sent and re-billed on every turn of
every run whether the tool is called or not.

Question 2 - confusability - is the one question a script cannot answer.
It is judgement, and it is argued in D2a_tool_design.md.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "A2_scaffold"))

import config      # noqa: E402
import prompt      # noqa: E402
import tools       # noqa: E402

RULE = "=" * 72

# The brief names a minimum set for Problem A. Anything we ship beyond
# it has to earn its place out loud.
BRIEF_MINIMUM = {"get_claim", "lookup_policy", "check_coverage",
                 "get_preauthorisation", "lookup_hospital",
                 "issue_decision_letter"}


def load():
    root = config.data_root()
    claims = json.load(open(os.path.join(root, "data_A", "claims.json"),
                            encoding="utf-8"))
    labels = json.load(open(os.path.join(root, "expected_outcomes_A.json"),
                            encoding="utf-8"))
    return claims, {l["case_id"]: l for l in labels}


def turns_on(claims, labels):
    """Which cases turn on the fact each tool alone returns."""
    by_id = {c["claim_id"]: c for c in claims}
    hit = {name: [] for name in tools.REGISTRY["A"]}

    for case_id, label in labels.items():
        claim = by_id.get(case_id)
        if claim is None:
            continue
        fam = label.get("family", "")
        blob = (" ".join(label.get("must_record", [])) + " " + fam).lower()

        # get_claim - the entry point. Every case needs the lines.
        hit["get_claim"].append(case_id)

        # lookup_policy - status, dates, limit, exclusions all live here.
        pol = tools.lookup_policy(claim["member_id"])
        if pol:
            p = pol["policy"]
            if (p["status"] != "active" or p["exclusions"]
                    or "limit" in blob or "laps" in blob or "date" in blob):
                hit["lookup_policy"].append(case_id)

        # lookup_hospital - ONE boolean, and nothing else returns it.
        hosp = tools.lookup_hospital(claim["hospital_id"])
        if hosp and not hosp["panel"]:
            hit["lookup_hospital"].append(case_id)

        # check_coverage - every line has to be checked.
        hit["check_coverage"].append(case_id)

        # get_preauthorisation - only where coverage demands one.
        policy_id = pol["policy"]["policy_id"] if pol else None
        for line in claim["lines"]:
            cov = tools.check_coverage(line["code"], policy_id)
            if cov["requires_preauth"]:
                hit["get_preauthorisation"].append(case_id)
                break

        # check_duplicate_claim - the one tool beyond the brief's minimum.
        if tools.check_duplicate_claim(
                member_id=claim["member_id"],
                hospital_id=claim["hospital_id"],
                date_of_service=claim["date_of_service"],
                lines=claim["lines"]) is not None:
            hit["check_duplicate_claim"].append(case_id)

        # issue_decision_letter - written unless the case escalates.
        if label.get("expected_decision") != "escalate":
            hit["issue_decision_letter"].append(case_id)

    return hit


def prefix_cost():
    """Tokens each descriptor adds to the prefix of EVERY turn."""
    was = config.PROMPT_VERSION
    config.PROMPT_VERSION = "v2"
    try:
        return {name: len(prompt.format_descriptor(tools.DESCRIPTORS[name])) // 4
                for name in tools.REGISTRY["A"]}
    finally:
        config.PROMPT_VERSION = was


# The eighth tool we did not add. Written in the same shape and to the
# same standard as the seven that shipped, so the comparison is between
# two real descriptors and not between ours and a strawman.
NOT_ADDED = {
    "name": "check_required_documents",
    "signature": "check_required_documents(code: str, policy_id: str) -> "
                 "{code, required_document: str | None} | None",
    "purpose": "Which document, if any, a line cannot be paid without.",
    "when": "ONCE PER LINE, after check_coverage, before deciding the line.",
    "args": {"code": "str, ONE line's procedure code. A code not in the "
                     "catalogue returns None.",
             "policy_id": "str, REQUIRED, from lookup_policy. Requirements "
                          "are per-policy, so this cannot be omitted."},
    "returns": "{code, required_document (str or None)}",
    "returns_bound": "exactly 1 record, at most ~18 tokens.",
    "failure": "Returns None for an unknown code or policy. A null "
               "required_document means the line needs no document - it does "
               "NOT mean the document is missing.",
    "irreversible": "No - read only.",
}


def counterfactual(cost):
    """Move 2 against move 4, on the one decision where we faced the choice.

    `required_document` could have been a tool. It became a field on a
    call the agent was already making. The brief asks which of the four
    moves we tried; this is what the other answer would have cost.
    """
    added = len(prompt.format_descriptor(NOT_ADDED)) // 4

    # Measured in measure_return_sizes.py, summed over the 41
    # check_coverage calls the current queue makes: 1655 tokens with the
    # field against 1340 without. Not 7 x 41 - 7 is the worst case and
    # most calls pay less.
    field_total = 1655 - 1340
    field_calls = 41

    # A tool is re-sent every turn of every run, called or not. Runs on
    # the scripted backend average a little over 4 turns per case.
    turns_per_case, cases, trials = 4, 25, 3
    tool_total = added * turns_per_case * cases * trials

    print(RULE)
    print("  THE TOOL WE DID NOT ADD · move 2 against move 4")
    print(RULE)
    print("  Both deliver the same fact: which document a line needs.")
    print()
    print("  move 4 · ship check_required_documents")
    print("      %d tokens of descriptor, re-sent every turn whether or" % added)
    print("      not the line needs a document")
    print("      %d turns x %d cases x %d trials = %d tokens a pass"
          % (turns_per_case, cases, trials, tool_total))
    print("      and one extra call per line, so more turns, not fewer")
    print()
    print("  move 2 · return more from check_coverage")
    print("      0 tokens of descriptor - the tool was already there")
    print("      measured across %d calls = %d tokens a pass"
          % (field_calls, field_total))
    print("      no extra call: the fact arrives in a turn already spent")
    print()
    print("  %d against %d - about %.0fx - for the same fact."
          % (tool_total, field_total, tool_total / field_total))
    print("  And the prefix cost is the part that does not go away when")
    print("  a case has no document requirement at all.")
    print()


def main():
    claims, labels = load()
    hit = turns_on(claims, labels)
    cost = prefix_cost()
    total = sum(cost.values())
    n = len(labels)

    print()
    print(RULE)
    print("  Q1 · WHICH CASES TURN ON THIS TOOL, out of %d" % n)
    print("  Q3 · WHAT ITS DESCRIPTOR COSTS, every turn, called or not")
    print(RULE)
    print("  %-24s %-8s %-7s %-9s %s"
          % ("tool", "cases", "share", "tokens", "in brief's min set"))
    print("  " + "-" * 66)
    for name in sorted(hit, key=lambda t: -len(hit[t])):
        cases = hit[name]
        print("  %-24s %-8s %-7s %-9s %s"
              % (name, "%d" % len(cases), "%d%%" % (100 * len(cases) / n),
                 cost[name], "yes" if name in BRIEF_MINIMUM else "NO - ours"))
    print("  " + "-" * 66)
    print("  %-24s %-8s %-7s %-9s" % ("TOTAL PREFIX", "", "", total))
    print()

    print(RULE)
    print("  THE NARROW ONES, named")
    print(RULE)
    for name in sorted(hit, key=lambda t: len(hit[t])):
        cases = hit[name]
        if len(cases) > n // 3:
            continue
        per = cost[name] / len(cases) if cases else float("inf")
        print("\n  %s - %d case(s), %d prefix tokens"
              % (name, len(cases), cost[name]))
        print("      %s" % (", ".join(cases) if cases
                            else "NONE. No case turns on it."))
        print("      %.0f prefix tokens per case it decides" % per)
    print()

    counterfactual(cost)

    print(RULE)
    print("  Beyond the brief's minimum set:")
    extra = sorted(set(tools.REGISTRY["A"]) - BRIEF_MINIMUM)
    for name in extra:
        print("    %s - %d case(s) turn on it, %d tokens a turn"
              % (name, len(hit[name]), cost[name]))
    if not extra:
        print("    none")
    print(RULE)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
