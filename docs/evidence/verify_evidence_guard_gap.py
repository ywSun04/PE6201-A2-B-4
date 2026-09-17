#!/usr/bin/env python3
"""
D2(a) x D3(b) · check_evidence and the line that is not payable yet.
A regression test, kept after the fix rather than deleted with it.

    python3 docs/evidence/verify_evidence_guard_gap.py

NOTHING IN guardrails.py IS MODIFIED BY THIS FILE. It holds a frozen copy
of check_evidence AS IT WAS BEFORE THE FIX, runs the affected cases
through that, then runs them again through guardrails.py as it stands,
and prints both columns. Exits non-zero if the current guard stops
producing the right answers - so if anyone ever removes the three lines,
this says so instead of the failure resurfacing in a live battery.

--------------------------------------------------------------------
WHAT THE BUG WAS

check_evidence re-derives the payable total and compares it with the
total the agent is writing. Its per-line logic was:

    excluded              -> skip, not payable
    requires_preauth      -> payable only if an approval was found
    otherwise             -> payable

Since v2 there is a third way for a line not to be payable: coverage now
returns `required_document`, and a line whose required document was not
attached cannot be settled - it is the SUBJECT of the ask. check_evidence
did not know that field existed, so it counted such a line as payable,
recomputed a total the agent had correctly not written, and halted with
evidence_mismatch. The record then read `decision: escalate`.

WHY IT WAS WORTH CHASING DOWN. check_evidence is reached from gate(),
which sits in front of issue_decision_letter on EVERY backend - only
`approve` differs between scripted and live. So this was not a scripted
artefact: it would have fired for all five v2 models and the v1 run
alike, on roughly 16% of the set, and the cause would have looked like a
model weakness in the D5(b) table rather than a guard defect.

The guard was not wrong to exist and was not wrong about anything it had
been told. It was missing one fact that did not exist when it was
written - the same class of bug it was built to catch.

THE FIX, three lines symmetric to the `excluded` test above them: both
say 'this line is not payable, so it is not in the total'.
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

FIX = '''
    # guardrails.Guardrails.check_evidence, inside the per-line loop,
    # directly after the `excluded` test:

            cov = tools.check_coverage(code, policy_id)
            if cov is None or cov["excluded"]:
                continue
+           needed = cov.get("required_document")
+           if needed and needed not in set(claim.get("documents") or []):
+               continue      # the subject of an ask, not a settled line
            if cov["requires_preauth"]:
'''


def unfixed_check_evidence(self, action_name, payload):
    """check_evidence as it stood BEFORE the fix - the three lines absent.

    Frozen here on purpose. Reading the old behaviour out of git history
    every time would make this test depend on history staying tidy; a
    copy makes the comparison stand on its own.
    """
    if action_name != "issue_decision_letter":
        return
    claim_id = payload.get("claim_id")
    claim = tools.get_claim(claim_id)
    if claim is None:
        return

    pol = tools.lookup_policy(claim["member_id"])
    policy_id = pol["policy"]["policy_id"] if pol else None
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
        # the three lines are absent here - that is the whole difference
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

    live = guardrails.Guardrails.check_evidence
    guardrails.Guardrails.check_evidence = unfixed_check_evidence
    try:
        before = run_column()
    finally:
        guardrails.Guardrails.check_evidence = live
    after = run_column()

    print(RULE)
    print("  every case below is labelled %r" % EXPECTED)
    print(RULE)
    print("  %-10s %-26s %-26s" % ("case", "before the fix", "guardrails.py today"))
    print("  " + "-" * 64)
    for case_id in CASES:
        b, a = before[case_id][0], after[case_id][0]
        flag = "" if b == a else "<- the three lines"
        print("  %-10s %-26s %-26s %s" % (case_id, b, a, flag))
    print()

    stops = [(c, before[c][2]) for c in CASES if before[c][1]]
    if stops:
        print("  what the old guard said when it halted")
        for case_id, reason in stops:
            print("    %-10s %s" % (case_id, reason.split(" - ", 1)[-1]))
        print()

    n_before = sum(1 for c in CASES if before[c][0] == EXPECTED)
    n_after = sum(1 for c in CASES if after[c][0] == EXPECTED)
    print("  correct before : %d of %d" % (n_before, len(CASES)))
    print("  correct today  : %d of %d" % (n_after, len(CASES)))
    print()
    print(FIX)

    unchanged = [c for c in CASES if before[c][0] == after[c][0]]
    if unchanged:
        print("  %s unchanged - the control. No required document on those"
              % ", ".join(unchanged))
        print("  lines, so the added test never fires and the guard behaves")
        print("  exactly as it always did.")
        print()

    print(RULE)
    if n_after == len(CASES):
        print("  PASS · the guard settles all %d correctly." % len(CASES))
    else:
        print("  FAIL · %d of %d are wrong with guardrails.py as it stands."
              % (len(CASES) - n_after, len(CASES)))
        print("  If the three lines were just removed, that is why.")
    print(RULE)
    print()
    return 0 if n_after == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(main())
