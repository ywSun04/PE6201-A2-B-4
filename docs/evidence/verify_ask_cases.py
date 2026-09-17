#!/usr/bin/env python3
"""
D4 EVIDENCE · are the four new ASK labels derivable from the tools?

    python3 docs/evidence/verify_ask_cases.py

A label nobody can reach is a broken case, and it fails quietly: the agent
looks wrong when the answer key was. So before CLM-9401..9404 go near a
model, this walks each one through the tool layer the way a correct agent
would, derives the outcome from what comes back, and compares it with the
label that was written for it.

It also states, for each case, THE SHORTCUT IT EXISTS TO BREAK, and checks
that the shortcut really does get this case wrong. A near-miss that both
the careful and the careless agent get right is not testing anything.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "A2_scaffold"))

import config      # noqa: E402
import tools       # noqa: E402

CASES = ["CLM-9401", "CLM-9402", "CLM-9403", "CLM-9404"]
RULE = "=" * 72


def key_for(case_id):
    path = os.path.join(config.data_root(), "expected_outcomes_A.json")
    rows = json.load(open(path, encoding="utf-8"))
    return {r["case_id"]: r for r in rows}[case_id]


def decide(case_id):
    """What a correct agent concludes, derived only from tool answers.

    Deliberately NOT a copy of the agent's logic - it is the routing table
    read straight off Appendix A, applied to observations. If this and the
    label disagree, one of the two is wrong and both are mine.
    """
    claim = tools.get_claim(case_id)
    pol = tools.lookup_policy(claim["member_id"])
    policy, remaining = pol["policy"], pol["remaining"]
    attached = set(claim["documents"])
    trace = []

    if policy["status"] != "active":
        return "escalate", "policy_lapsed", trace
    if not (policy["start_date"] <= claim["date_of_service"]
            <= policy["end_date"]):
        return "escalate", "outside_policy_dates", trace
    if sum(l["amount"] for l in claim["lines"]) > remaining:
        return "escalate", "annual_limit_exceeded", trace

    asks, refused = [], []
    for line in claim["lines"]:
        cov = tools.check_coverage(line["code"], policy["policy_id"])
        if cov["excluded"]:
            refused.append("%s refused under %s"
                           % (line["code"], cov["exclusion_rule"]))
            trace.append("%s excluded -> %s" % (line["code"],
                                                cov["exclusion_rule"]))
            continue
        need = cov["required_document"]
        if need and need not in attached:
            asks.append("%s for line %s" % (need.replace("_", " "),
                                            line["code"]))
            trace.append("%s needs %s, attached=%s -> ASK"
                         % (line["code"], need, sorted(attached) or "nothing"))
            continue
        if cov["requires_preauth"]:
            pa = tools.get_preauthorisation(claim["member_id"], line["code"],
                                            claim["date_of_service"])
            if pa is None:
                asks.append("pre-authorisation for line %s valid on %s"
                            % (line["code"], claim["date_of_service"]))
                trace.append("%s needs pre-auth, none valid on %s -> ASK"
                             % (line["code"], claim["date_of_service"]))
                continue
            trace.append("%s pre-auth %s valid -> payable"
                         % (line["code"], pa["preauth_id"]))
        else:
            trace.append("%s payable" % line["code"])

    if asks:
        return "request_document", asks, trace + refused
    return "approve_in_principle", None, trace + refused


# ---- the shortcuts each case is built to break ----------------------
def shortcut_empty_documents(claim, *_):
    """'documents is a non-empty list, so the paperwork is fine.'"""
    return "approve_in_principle" if claim["documents"] else "request_document"


def shortcut_preauth_is_the_last_gate(claim, policy_id):
    """'a valid pre-authorisation means the line is payable.'"""
    for line in claim["lines"]:
        cov = tools.check_coverage(line["code"], policy_id)
        if cov["requires_preauth"] and tools.get_preauthorisation(
                claim["member_id"], line["code"],
                claim["date_of_service"]) is None:
            return "request_document"
    return "approve_in_principle"


def shortcut_only_upper_bound(claim, _policy_id):
    """'the approval has not expired, so it authorises the claim.'"""
    path = os.path.join(config.data_root(), "data_A", "preauthorisations.json")
    for pa in json.load(open(path, encoding="utf-8")):
        for line in claim["lines"]:
            if (pa["member_id"] == claim["member_id"]
                    and pa["procedure_code"] == line["code"]
                    and claim["date_of_service"] <= pa["valid_to"]):
                return "approve_in_principle"
    return "request_document"


def shortcut_excluded_means_escalate(claim, policy_id):
    """'a line the policy excludes is a reason to escalate the claim.'"""
    for line in claim["lines"]:
        if tools.check_coverage(line["code"], policy_id)["excluded"]:
            return "escalate"
    return "approve_in_principle"


SHORTCUTS = {
    "CLM-9401": ("documents is non-empty, so the paperwork is fine",
                 shortcut_empty_documents),
    "CLM-9402": ("a valid pre-authorisation is the last gate",
                 shortcut_preauth_is_the_last_gate),
    "CLM-9403": ("the approval has not expired, so it applies",
                 shortcut_only_upper_bound),
    "CLM-9404": ("an excluded line means escalate the claim",
                 shortcut_excluded_means_escalate),
}


def main():
    print()
    print(config.summary())
    print()
    ok = True

    for case_id in CASES:
        key = key_for(case_id)
        claim = tools.get_claim(case_id)
        policy_id = tools.lookup_policy(claim["member_id"])["policy"]["policy_id"]
        decision, detail, trace = decide(case_id)

        print(RULE)
        print("  %s · %s" % (case_id, key["family"]))
        print(RULE)
        print("  documents attached : %s" % (claim["documents"] or "none"))
        for step in trace:
            print("    %s" % step)
        print()

        label_ok = decision == key["expected_decision"]
        print("  derived  : %s" % decision)
        print("  labelled : %s" % key["expected_decision"])
        print("  %s" % ("MATCH" if label_ok else "MISMATCH - fix one of them"))

        if decision == "request_document":
            # Compare on the LINE CODE, not on the sentence. The label is
            # written for a human to read ("pre-authorisation reference for
            # line 29881, valid on ...") and the derivation builds its own
            # wording; matching those as strings tests punctuation, not the
            # case. What must agree is WHICH LINE the ask is about.
            named = key.get("missing", "")
            asked_lines = {c for line in claim["lines"]
                           for c in [line["code"]]
                           if any(c in d for d in detail)}
            covered = bool(asked_lines) and any(c in named for c in asked_lines)
            print("  missing  : %s" % key.get("missing"))
            print("  lines this run asked about: %s" % ", ".join(sorted(asked_lines)))
            print("  %s" % ("the label names one of them"
                            if covered else
                            "MISMATCH - the label asks about a line nothing flagged"))
            label_ok = label_ok and covered

        blurb, shortcut = SHORTCUTS[case_id]
        got = shortcut(claim, policy_id)
        breaks = got != key["expected_decision"]
        print()
        print("  shortcut it breaks: \"%s\"" % blurb)
        print("    that shortcut answers %s, the truth is %s  -> %s"
              % (got, key["expected_decision"],
                 "BREAKS IT" if breaks else "NO DISCRIMINATION, case is weak"))
        print()
        ok = ok and label_ok and breaks

    print(RULE)
    print("  %s" % ("All four labels derive from the tools, and each one "
                    "breaks its shortcut." if ok else
                    "Something above did not hold - read it before committing."))
    print(RULE)
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
