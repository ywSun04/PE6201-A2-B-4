#!/usr/bin/env python3
"""
D2(b) EVIDENCE · does every shipped tool carry the brief's six fields?

    python3 docs/evidence/verify_descriptor_contract.py

The brief is explicit - "Every tool ships a descriptor contract. Six
fields, no exceptions" - and the six it names are NOT the six the
scaffold shipped:

    the brief asks for          the scaffold had
    ------------------------    ----------------------------------
    NAME + SIGNATURE            name          (no types, no return)
    WHAT                        purpose       ok
    INPUT + what a bad value    args          type and provenance only
      does
    RETURNS + a SIZE BOUND      returns       shape only, no bound
    FAILS WHEN                  failure       ok
    IRREVERSIBLE? + the gate    -             absent entirely
                                when          extra, and worth keeping

Six fields either way, which is exactly why the gap is easy to miss: the
count matches and three of the contents do not. This check reads the
requirement rather than the count.

Problem A only. The team submits A, and B's descriptors are left in the
shape they shipped - noted here rather than silently skipped.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "A2_scaffold"))

import tools       # noqa: E402

RULE = "=" * 72

# field, what the brief demands of it, how to tell it was actually done
REQUIRED = [
    ("signature", "NAME + SIGNATURE, with types and a return type",
     lambda v: "(" in v and "->" in v),
    ("purpose", "WHAT it answers that nothing else does",
     lambda v: len(v) > 10),
    ("args", "INPUT - each argument, its type, and what a bad value does",
     lambda v: isinstance(v, dict)),
    ("returns", "RETURNS - the shape",
     lambda v: len(v) > 10),
    ("returns_bound", "RETURNS - a SIZE BOUND",
     lambda v: "token" in v.lower()),
    ("failure", "FAILS WHEN - the named conditions",
     lambda v: len(v) > 10),
    ("irreversible", "IRREVERSIBLE? yes/no, and if yes the gate",
     lambda v: v.strip().lower().startswith(("yes", "no"))),
]

# INPUT has a second requirement the brief spells out: what a bad value
# does. A type alone is not the contract.
BAD_VALUE_WORDS = ("raise", "none", "null", "refus", "not on file",
                   "unknown", "checked", "cannot")


def main():
    names = sorted(tools.REGISTRY["A"])
    print()
    print(RULE)
    print("  PROBLEM A · %d tools, against the brief's six fields" % len(names))
    print(RULE)

    failures = []
    for name in names:
        d = tools.DESCRIPTORS.get(name)
        print("\n  %s" % name)
        if d is None:
            print("      NO DESCRIPTOR AT ALL")
            failures.append((name, "missing descriptor"))
            continue

        for field, demand, ok in REQUIRED:
            value = d.get(field)
            if value is None:
                print("      MISSING  %-14s %s" % (field, demand))
                failures.append((name, "no %s" % field))
            elif not ok(value):
                print("      WEAK     %-14s %s" % (field, demand))
                failures.append((name, "%s does not meet the field" % field))
            else:
                print("      ok       %-14s" % field)

        # the extra INPUT requirement
        blob = " ".join(str(v) for v in d.get("args", {}).values()).lower()
        if d.get("args") and not any(w in blob for w in BAD_VALUE_WORDS):
            print("      WEAK     args           no argument says what a bad "
                  "value does")
            failures.append((name, "args state types but not bad values"))

    print()
    print(RULE)
    if failures:
        print("  %d problem(s):" % len(failures))
        for name, why in failures:
            print("    %-24s %s" % (name, why))
    else:
        print("  All %d Problem A tools carry all six fields." % len(names))
        print()
        print("  Note what this does NOT check: whether the words are any")
        print("  good. A size bound can be present and wrong. The bounds")
        print("  here were measured, not estimated - see")
        print("  measure_return_sizes.py, which is where the numbers in")
        print("  every returns_bound came from.")
    print(RULE)
    print()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
