#!/usr/bin/env python3
"""
D5(b) · Harry's live battery - google/gemini-3.8-flash.

Copied from run_live_battery.py (Sun Yawen's, hardcoded to her model and
her output file) rather than edited in place, so the two of us never race
on the same ASSIGNED model or the same results file. Same mechanics,
same checkpoint-and-resume behaviour, same "never touches config.py on
disk" guarantee - only ASSIGNED and OUT differ.

    python3 docs/evidence/run_live_battery_harry.py              # all cases
    python3 docs/evidence/run_live_battery_harry.py CLM-8842     # one case, verbose
    python3 docs/evidence/run_live_battery_harry.py --smoke      # one cheap check

Requires OPENROUTER_API_KEY in the environment. Never writes the key,
never edits config.py on disk. Results land in
docs/evidence/live_results_harry.json after EVERY trial so a timeout
cannot void the spend so far. Re-running skips trials already in that
file.

A marker clone still runs scripted — this file is how we arm live.
"""
import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "A2_scaffold"))

import config      # noqa: E402

ASSIGNED = "google/gemini-3.8-flash"
OUT = os.path.join(HERE, "live_results_harry.json")


def arm_live():
    if not os.environ.get("OPENROUTER_API_KEY"):
        sys.exit("OPENROUTER_API_KEY is not set. Nothing was spent.")
    config.BACKEND = "live"
    config.MODEL = ASSIGNED
    config.API_KEY = os.environ["OPENROUTER_API_KEY"]
    config.PRICE_IN, config.PRICE_OUT = config.prices()
    config.ARMED_IN_MEMORY = True


def load_checkpoint():
    if not os.path.isfile(OUT):
        return [], []
    with open(OUT, encoding="utf-8") as fh:
        blob = json.load(fh)
    return blob.get("results") or [], blob.get("judgement_queue") or []


def save(results, queue, summary=None):
    payload = {"config": config.summary(), "summary": summary,
               "results": results, "judgement_queue": queue}
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, OUT)


def main(argv):
    sys.stdout.reconfigure(line_buffering=True)
    arm_live()
    from agent import run_case                         # noqa: E402
    from harness import (                              # noqa: E402
        code_check, load_cases, load_key, prepare_judgement_check,
        report, run_set)

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
        results, queue = run_set(cases, verbose=verbose, trials_for=trials_for)
        summary = report(results)
        save(results, queue, summary)
        print("  Wrote %s" % OUT, flush=True)
        return 0 if summary["passed"] == summary["trials"] else 1

    if args:
        cases = args
        verbose = True
        trials_for = lambda cid: 1
    else:
        cases = load_cases()
        verbose = False
        trials_for = None

    key = load_key()
    if trials_for is None:
        from harness import _is_negative
        trials_for = lambda cid: 3 if _is_negative(key.get(cid)) else 1

    results, queue = load_checkpoint()
    done = {(r["case_id"], r["trial"]) for r in results}
    queued = {q["case_id"] for q in queue}
    if done:
        print("  Resuming: %d trial(s) already on disk." % len(done),
              flush=True)

    for cid in cases:
        expected = key.get(cid)
        if expected is None:
            print("  SKIP %s - no label" % cid, flush=True)
            continue
        n = trials_for(cid)
        for trial in range(1, n + 1):
            if (cid, trial) in done:
                print("  skip %s trial %d (checkpoint)" % (cid, trial),
                      flush=True)
                continue
            print("  run  %s trial %d/%d ..." % (cid, trial, n), flush=True)
            try:
                record = run_case(cid, verbose=verbose)
            except Exception as err:                    # noqa: BLE001
                print("      NETWORK/HARNESS: %s: %s"
                      % (type(err).__name__, err), flush=True)
                traceback.print_exc()
                record = {
                    "decision": "escalate",
                    "reason": "live call failed - %s: %s"
                              % (type(err).__name__, err),
                    "case_id": cid, "evidence": [], "turns": 0,
                    "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0,
                    "seconds": 0, "guardrails_fired": [],
                    "stopped_by": "live_call_failed", "backend": "live",
                }
            passed, fails = code_check(record, expected)
            results.append({"case_id": cid, "trial": trial, "passed": passed,
                            "fails": fails, "record": record,
                            "family": expected.get("family")})
            if cid not in queued:
                queue.append(prepare_judgement_check(record, expected))
                queued.add(cid)
            save(results, queue)
            mark = "PASS" if passed else "FAIL"
            print("      %s  decision=%s  cost=US$%.4f  turns=%s"
                  % (mark, record.get("decision"),
                     record.get("cost_usd") or 0,
                     record.get("turns")), flush=True)

    summary = report(results)
    save(results, queue, summary)
    print("  Wrote %s" % OUT, flush=True)
    print()
    return 0 if summary["passed"] == summary["trials"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
