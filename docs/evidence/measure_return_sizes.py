#!/usr/bin/env python3
"""
D2(b) EVIDENCE · tokens RETURNED per call, per tool, v1 against v2.

    python3 docs/evidence/measure_return_sizes.py

Two jobs, one pass over the data.

  1. THE D2(b) NUMBER. The brief asks for "tokens returned per call" for
     the v1 and the v2 of one tool. check_coverage is that tool, and its
     two return shapes differ by the `required_document` field, so the
     cost of carrying that field is measured here rather than asserted.

  2. THE SIZE BOUND every descriptor has to state. A bound written from
     memory is a guess; these are measured over every claim currently in
     the queue, so the descriptors can quote a real worst case.

Tokens are chars/4, the same rough rule the scaffold uses everywhere
else. It is not a tokeniser and does not need to be - what matters is
that both arms are counted the same way.
"""
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "A2_scaffold"))

import config      # noqa: E402
import tools       # noqa: E402

RULE = "=" * 72


def tok(value):
    return len(json.dumps(value, ensure_ascii=False)) // 4


def every_call():
    """Every read-only call the agent could make, over every claim."""
    path = os.path.join(config.data_root(), "data_A", "claims.json")
    claims = json.load(open(path, encoding="utf-8"))
    out = {}

    def note(tool_name, value):
        out.setdefault(tool_name, []).append(tok(value))

    for claim in claims:
        note("get_claim", claim)
        pol = tools.lookup_policy(claim["member_id"])
        note("lookup_policy", pol)
        note("lookup_hospital", tools.lookup_hospital(claim["hospital_id"]))
        policy_id = pol["policy"]["policy_id"]

        for line in claim["lines"]:
            cov = tools.check_coverage(line["code"], policy_id)
            note("check_coverage", cov)
            if cov["requires_preauth"]:
                note("get_preauthorisation",
                     tools.get_preauthorisation(claim["member_id"],
                                                line["code"],
                                                claim["date_of_service"]))

        note("check_duplicate_claim",
             tools.check_duplicate_claim(
                 member_id=claim["member_id"],
                 hospital_id=claim["hospital_id"],
                 date_of_service=claim["date_of_service"],
                 lines=claim["lines"]))

    # The gated write never reads anything, but its receipt is an
    # observation like any other and the agent pays for it.
    note("issue_decision_letter",
         tools.issue_decision_letter("CLM-8842", "approve_in_principle",
                                     3, 2180, 300))
    return out


def table(title, data):
    print(RULE)
    print("  %s" % title)
    print(RULE)
    print("  %-24s %5s %6s %6s %6s" % ("tool", "calls", "min", "median", "MAX"))
    print("  " + "-" * 52)
    for name in sorted(data):
        sizes = data[name]
        print("  %-24s %5d %6d %6d %6d"
              % (name, len(sizes), min(sizes),
                 round(statistics.median(sizes)), max(sizes)))
    print()
    return {n: max(s) for n, s in data.items()}


def main():
    print()
    print(config.summary())
    print()

    was = config.PROMPT_VERSION
    arms = {}
    try:
        for version in ("v1", "v2"):
            config.PROMPT_VERSION = version
            arms[version] = every_call()
    finally:
        config.PROMPT_VERSION = was

    worst_v1 = table("PROMPT_VERSION = v1 · tokens returned per call",
                     arms["v1"])
    worst_v2 = table("PROMPT_VERSION = v2 · tokens returned per call",
                     arms["v2"])

    print(RULE)
    print("  WHAT v2's EXTRA FIELD COSTS")
    print(RULE)
    for name in sorted(worst_v2):
        d = worst_v2[name] - worst_v1.get(name, 0)
        if d:
            m1 = statistics.mean(arms["v1"][name])
            m2 = statistics.mean(arms["v2"][name])
            print("  %-24s worst +%d tokens, mean %.1f -> %.1f  (+%.0f%%)"
                  % (name, d, m1, m2, 100 * (m2 - m1) / m1))
    print()

    cov1 = arms["v1"]["check_coverage"]
    cov2 = arms["v2"]["check_coverage"]
    print("  check_coverage is called once PER LINE. Over the %d calls the"
          % len(cov2))
    print("  current queue makes, carrying required_document costs")
    print("  %d - %d = %d tokens in total."
          % (sum(cov2), sum(cov1), sum(cov2) - sum(cov1)))
    print()
    print("  Set that against what it buys: without the field the whole")
    print("  required_document_absent family cannot be decided correctly by")
    print("  any model. See probe_tool_reachability.py.")
    print()

    print(RULE)
    print("  SIZE BOUNDS for the descriptors (v2 worst case, rounded up)")
    print(RULE)
    for name in sorted(worst_v2):
        print("  %-24s at most ~%d tokens" % (name, worst_v2[name]))
    print(RULE)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
