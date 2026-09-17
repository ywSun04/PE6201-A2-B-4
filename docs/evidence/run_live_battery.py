#!/usr/bin/env python3
"""
D5(b) · run the live battery without committing BACKEND = "live".

    python3 docs/evidence/run_live_battery.py              # all cases
    python3 docs/evidence/run_live_battery.py CLM-8842     # one case, verbose
    python3 docs/evidence/run_live_battery.py --smoke      # one cheap check

Requires OPENROUTER_API_KEY in the environment. Never writes the key,
never edits config.py on disk. Results land in
docs/evidence/live_results.json so the committed default stays scripted
- which is what a marker clones and runs.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "A2_scaffold"))

import config      # noqa: E402

ASSIGNED = "qwen/qwen3.8-flash"


def arm_live():
    if not os.environ.get("OPENROUTER_API_KEY"):
        sys.exit("OPENROUTER_API_KEY is not set. Nothing was spent.")
    config.BACKEND = "live"
    config.MODEL = ASSIGNED
    config.API_KEY = os.environ["OPENROUTER_API_KEY"]
    config.PRICE_IN, config.PRICE_OUT = config.prices()
    config.ARMED_IN_MEMORY = True


def main(argv):
    arm_live()
    from harness import load_cases, report, run_set   # noqa: E402

    print()
    print(config.summary())
    print("data: %s" % config.data_root())
    print()

    flags = {a for a in argv[1:] if a.startswith("-")}
    args = [a for a in argv[1:] if not a.startswith("-")]

    if "--smoke" in flags:
        cases = ["CLM-8842"]
        verbose = True
        trials_for = lambda cid: 1
    elif args:
        cases = args
        verbose = True
        trials_for = lambda cid: 1
    else:
        cases = load_cases()
        verbose = False
        trials_for = None

    results, queue = run_set(cases, verbose=verbose, trials_for=trials_for)
    summary = report(results)

    out = os.path.join(HERE, "live_results.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"config": config.summary(), "summary": summary,
                   "results": results, "judgement_queue": queue},
                  fh, indent=2, default=str)
    print("  Wrote %s" % out)
    print()
    return 0 if summary["passed"] == summary["trials"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
