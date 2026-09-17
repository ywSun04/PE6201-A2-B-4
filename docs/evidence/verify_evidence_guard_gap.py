#!/usr/bin/env python3
"""
FOR HARRY · a gap in check_evidence, reproduced and costed.
D2(a) x D3(b) integration, raised rather than patched.

    python3 docs/evidence/verify_evidence_guard_gap.py

NOTHING IN guardrails.py IS MODIFIED BY THIS FILE. It runs the affected
cases as they stand, then re-runs them with a three-line change applied
in memory only, and prints both columns. The change is yours to make or
refuse - this just makes the decision cheap.

--------------------------------------------------------------------
WHAT HAPPENS

check_evidence re-derives the payable total and compares it with the
total the agent is writing. Its per-line logic is:

    excluded              -> skip, not payable
    requires_preauth      -> payable only if an approval was found
    otherwise             -> payable

Since v2 there is a third way for a line not to be payable: coverage now
returns `required_document`, and a line whose required document was not
attached cannot be settled - it is the SUBJECT of the ask. check_evidence
does not know that field exists, so it counts such a line as payable,
recomputes a total the agent correctly did not write, and halts the run
with evidence_mismatch. The record then reads `decision: escalate`.

THIS IS NOT ONLY ABOUT THE NEW CASES. CLM-8901 ships with the assignment
and its expected decision is request_document. It cannot reach that
decision while this stands, so the `required_document_absent` family is
still unwinnable - for a different reason than before the tool fix.

The guard is not wrong to exist and it is not wrong about anything it was
told. It is simply missing one fact that did not exist when it was
written. Same class of bug as the one it was built to catch.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "A2_scaffold"))

import config        # noqa: E402
import guardrails    # noqa: E402
import tools         # noqa: E402
from agent import run_case              # noqa: E402
from guardrails import GuardrailStop    # noqa: E402

CASES = ["CLM-8901", "CLM-9401", "CLM-9402", "CLM-9403", "CLM-9404"]
EXPECTED = "request_document"
RULE = "=" * 72

PATCH = '''
    # in guardrails.Guardrails.check_evidence, inside the per-line loop,
    # directly after the `excluded` test:

            cov = tools.check_coverage(code, policy_id)
            if cov is None or cov["excluded"]:
                continue
+           needed = cov.get("required_document")
+           if needed and needed not in set(claim.get("documents") or []):
+               continue      # the subject of an ask, not a settled line
            if cov["requires_preauth"]:
'''


def patched_check_evidence(self, action_name, payload):
    """guardrails.check_evidence with the three lines added. Byte-for-byte
    the original otherwise, so the two columns below differ by that and
    nothing else."""
    if action_name != "issue_decision_letter":
        return
    claim_id = payload.get("claim_id")
    claim = tools.get_claim(claim_id)
    if claim is None:
        return

    pol = tools.lookup_policy(claim["member_id"])
    policy_id = pol["policy"]["policy_id"] if pol else None
    attached = set(claim.get("documents") or [])
    coverage_calls = {a.get("code") for t, a in self.calls_log
                      if t == "check_coverage"}
    preauth_calls = {a.get("procedure_code") for t, a in self.calls_log
                     if t == "get_preauthorisation"}

    missing, computed_total = [], 0
    for line in claim["lines"]:
        code = line["code"]
        if code not in coverage_calls:
            missing.append("no check_coverage for line %s" % code)
            continue
        cov = tools.check_coverage(code, policy_id)
        if cov is None or cov["excluded"]:
            continue
        # ---- the three added lines ----------------------------------
        needed = cov.get("required_document")
        if needed and needed not in attached:
            continue
        # -------------------------------------------------------------
        if cov["requires_preauth"]:
            if code not in preauth_calls:
                missing.append("no pre-authorisation check for line %s" % code)
                continue
            if tools.get_preauthorisation(claim["member_id"], code,
                                          claim["date_of_service"]) is not None:
                computed_total += line["amount"]
        else:
            computed_total += line["amount"]

    if missing:
        detail = "; ".join(missing)
        self._fire("evidence_missing", detail)
        raise GuardrailStop("evidence_missing", detail)

    written_total = payload.get("approved_total")
    if written_total is not None and written_total != computed_total:
        detail = ("approved_total %r does not match the recomputed %r"
                  % (written_total, computed_total))
        self._fire("evidence_mismatch", detail)
        raise GuardrailStop("evidence_mismatch", detail)


def run_column():
    out = {}
    for case_id in CASES:
        rec = run_case(case_id)
        out[case_id] = (rec["decision"], rec.get("stopped_by"),
                        rec.get("reason", ""))
    return out


def main():
    print()
    print(config.summary())
    print()

    before = run_column()

    original = guardrails.Guardrails.check_evidence
    guardrails.Guardrails.check_evidence = patched_check_evidence
    try:
        after = run_column()
    finally:
        guardrails.Guardrails.check_evidence = original

    print(RULE)
    print("  %-10s %-26s %-26s" % ("case", "as it stands", "with three lines added"))
    print(RULE)
    for case_id in CASES:
        b, a = before[case_id][0], after[case_id][0]
        print("  %-10s %-26s %-26s %s"
              % (case_id, b, a, "" if b == a else "<- changed"))
    print()

    print("  why each one halts today")
    for case_id in CASES:
        decision, stopped, reason = before[case_id]
        if stopped:
            print("    %-10s %s" % (case_id, reason.split(" - ", 1)[-1]))
    print()

    n_before = sum(1 for c in CASES if before[c][0] == EXPECTED)
    n_after = sum(1 for c in CASES if after[c][0] == EXPECTED)
    print(RULE)
    print("  reaching %r : %d of %d  ->  %d of %d"
          % (EXPECTED, n_before, len(CASES), n_after, len(CASES)))
    print(RULE)
    print(PATCH)
    print("  CLM-9403 is in the list and does NOT change, which is the")
    print("  control: its line has no required document, so the added test")
    print("  never fires and the guard behaves exactly as it does today.")
    print()
    print("  Harry - your call. The three lines are symmetric to the")
    print("  `excluded` test immediately above them: both say 'this line is")
    print("  not payable, so it is not in the total'. Nothing else in")
    print("  check_evidence moves, and no guardrail case of yours reaches")
    print("  this branch. If you would rather own the change, take it; if")
    print("  you would rather I made it, say so and I will.")
    print(RULE)
    print()
    return 0 if n_after == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(main())
