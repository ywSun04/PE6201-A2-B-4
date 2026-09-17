#!/usr/bin/env python3
"""
D2(a)/D2(b) EVIDENCE · Is every fact the answer key demands reachable
through the tool layer?

    python3 docs/evidence/probe_tool_reachability.py

The agent never reads the JSON files. It asks a tool a question and gets
one fact back. So a fact that no tool returns does not exist as far as
the agent is concerned - however good the model, however good the prompt,
however large the budget.

This probe asks that question at two grains, and for BOTH ARMS of the
D2(b) experiment, so the before and the after sit in one output:

  SECTION 1  file grain.  Which files under data_A/ does the tool layer
             read at all? Found by reading tools.py's own source for its
             _load() calls, so the answer cannot drift from the code.

  SECTION 2  case grain.  For CLM-8901 - whose answer key demands a named
             document - call EVERY tool the agent may call, collect every
             return value, and search all of them for the fact the key
             demands. Run once under v1 and once under v2.

EXIT 0 means the expected contrast held: unreachable under v1, reachable
under v2. If v1 ever comes back reachable, the two arms have drifted into
each other and the D2(b) comparison is no longer measuring anything.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SCAFFOLD = os.path.join(REPO, "A2_scaffold")
sys.path.insert(0, SCAFFOLD)

import config          # noqa: E402
import tools           # noqa: E402

CASE = "CLM-8901"
RULE = "=" * 72


def answer_key(case_id):
    path = os.path.join(config.data_root(), "expected_outcomes_A.json")
    rows = json.load(open(path, encoding="utf-8"))
    return {r["case_id"]: r for r in rows}[case_id]


def section_1_files():
    """Which data_A files does any tool actually open?"""
    print(RULE)
    print("  SECTION 1 - which data files can the agent reach at all?")
    print(RULE)

    src = open(os.path.join(SCAFFOLD, "tools.py"), encoding="utf-8").read()
    read_by_tools = set(re.findall(r'_load\(\s*"A"\s*,\s*"([a-z_]+)"', src))

    data_dir = os.path.join(config.data_root(), "data_A")
    on_disk = sorted(f[:-5] for f in os.listdir(data_dir) if f.endswith(".json"))

    unreachable = []
    for table in on_disk:
        ok = table in read_by_tools
        if not ok:
            unreachable.append(table)
        print("  %-26s %s" % (table, "read" if ok else "NOT READ BY ANY TOOL"))

    print()
    print("  %d of %d files reachable.%s"
          % (len(on_disk) - len(unreachable), len(on_disk),
             "  UNREACHABLE: " + ", ".join(unreachable) if unreachable else ""))
    print()
    return unreachable


def section_2_case(version, verbose):
    """Call every tool for CLM-8901 under one version; hunt for the fact."""
    was = config.PROMPT_VERSION
    config.PROMPT_VERSION = version
    try:
        claim = tools.get_claim(CASE)
        line = claim["lines"][0]
        pol = tools.lookup_policy(claim["member_id"])

        # Everything the agent may call for this claim. The gated write is
        # excluded: it is not a way to learn a fact.
        calls = [
            ("get_claim", {"claim_id": CASE}),
            ("lookup_policy", {"member_id": claim["member_id"]}),
            ("lookup_hospital", {"hospital_id": claim["hospital_id"]}),
            ("check_coverage", {"code": line["code"],
                                "policy_id": pol["policy"]["policy_id"]}),
            ("get_preauthorisation", {"member_id": claim["member_id"],
                                      "procedure_code": line["code"],
                                      "date_of_service": claim["date_of_service"]}),
            ("check_duplicate_claim", {"member_id": claim["member_id"],
                                       "hospital_id": claim["hospital_id"],
                                       "date_of_service": claim["date_of_service"],
                                       "lines": claim["lines"]}),
        ]

        blobs = []
        for name, args in calls:
            result = tools.call("A", name, args)
            blob = json.dumps(result, ensure_ascii=False)
            blobs.append(blob)
            if verbose:
                print("  %s" % name)
                print("      -> %s"
                      % (blob if len(blob) <= 260 else blob[:260] + " ...[cut]"))
        return "itemised_bill" in " ".join(blobs), len(calls)
    finally:
        config.PROMPT_VERSION = was


def main():
    print()
    print(config.summary())
    print("data: %s" % config.data_root())
    print()

    section_1_files()

    key = answer_key(CASE)
    print(RULE)
    print("  SECTION 2 - %s, every tool called, every answer searched" % CASE)
    print(RULE)
    print("  answer key demands")
    print("    expected_decision : %s" % key["expected_decision"])
    print("    missing           : %s" % key.get("missing"))
    print("    family            : %s" % key["family"])
    print()
    print("  The claim attaches documents: %s" % json.dumps(
        tools.get_claim(CASE)["documents"]))
    print("  So the agent can see the cupboard is empty. The question is")
    print("  whether anything tells it what was supposed to be in it.")
    print()

    found = {}
    for version in ("v1", "v2"):
        print("  ---- PROMPT_VERSION = %s %s" % (version, "-" * 44))
        found[version], n = section_2_case(version, verbose=(version == "v2"))
        print("      searched %d tool answers for 'itemised_bill' : %s"
              % (n, "FOUND" if found[version] else "NOT FOUND"))
        print()

    print(RULE)
    print("  VERDICT")
    print(RULE)
    expected = (found["v1"] is False and found["v2"] is True)
    print("  v1  fact unreachable -> %s cannot be decided correctly by ANY"
          % CASE)
    print("      model. The key demands %r and no" % key.get("missing"))
    print("      tool returns it. The whole `%s` family" % key["family"])
    print("      is unwinnable. A tool-set defect, not a prompt defect.")
    print()
    print("  v2  check_coverage carries `required_document`, so the fact")
    print("      arrives on a call the agent was already making, in a turn")
    print("      it was already spending. No new tool, no new turn.")
    print()
    print("  %s" % ("AS EXPECTED - the two arms differ in the way D2(b) claims."
                    if expected else
                    "UNEXPECTED - v1=%s v2=%s. The arms have drifted; the "
                    "D2(b) comparison is no longer sound."
                    % (found["v1"], found["v2"])))
    print(RULE)
    print()
    return 0 if expected else 1


if __name__ == "__main__":
    sys.exit(main())
