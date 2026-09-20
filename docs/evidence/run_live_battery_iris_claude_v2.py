#!/usr/bin/env python3
"""Run Iris's D5(b) Claude Haiku v2 battery without editing config.py."""
import json
import os
import sys
import traceback
from urllib.error import HTTPError

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "A2_scaffold"))

import config  # noqa: E402

ASSIGNED = "anthropic/claude-haiku-4.5"
OUT = os.path.join(HERE, "live_results_iris_claude_v2.json")


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
    from agent import run_case  # noqa: E402
    from harness import (  # noqa: E402
        code_check, load_cases, load_key, prepare_judgement_check, report,
    )

    print("\n" + config.summary())
    print("data: %s\n" % config.data_root())

    cases = load_cases()
    key = load_key()
    from harness import _is_negative
    trials_for = lambda cid: 3 if _is_negative(key.get(cid)) else 1

    results, queue = load_checkpoint()
    done = {(r["case_id"], r["trial"]) for r in results}
    queued = {q["case_id"] for q in queue}
    if done:
        print("Resuming: %d trial(s) already on disk." % len(done))

    for cid in cases:
        expected = key.get(cid)
        if expected is None:
            print("SKIP %s - no label" % cid)
            continue
        for trial in range(1, trials_for(cid) + 1):
            if (cid, trial) in done:
                print("skip %s trial %d" % (cid, trial))
                continue
            print("run  %s trial %d/%d ..." % (cid, trial, trials_for(cid)))
            try:
                record = run_case(cid, verbose=False)
            except HTTPError as err:
                if err.code in (401, 402):
                    print("STOP: OpenRouter rejected the request (%s). No failed trial was recorded." % err)
                    summary = report(results)
                    save(results, queue, summary)
                    return 2
                raise
            except Exception as err:  # noqa: BLE001
                print("NETWORK/HARNESS: %s: %s" % (type(err).__name__, err))
                traceback.print_exc()
                record = {
                    "decision": "escalate", "reason": "live call failed - %s: %s" % (type(err).__name__, err),
                    "case_id": cid, "evidence": [], "turns": 0, "tokens_in": 0,
                    "tokens_out": 0, "cost_usd": 0.0, "seconds": 0,
                    "guardrails_fired": [], "stopped_by": "live_call_failed", "backend": "live",
                }
            passed, fails = code_check(record, expected)
            results.append({"case_id": cid, "trial": trial, "passed": passed,
                            "fails": fails, "record": record,
                            "family": expected.get("family")})
            if cid not in queued:
                queue.append(prepare_judgement_check(record, expected))
                queued.add(cid)
            save(results, queue)
            print("%s  decision=%s  cost=US$%.4f  turns=%s" % (
                "PASS" if passed else "FAIL", record.get("decision"),
                record.get("cost_usd") or 0, record.get("turns")))

    summary = report(results)
    save(results, queue, summary)
    print("Wrote %s" % OUT)
    return 0 if summary["passed"] == summary["trials"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
