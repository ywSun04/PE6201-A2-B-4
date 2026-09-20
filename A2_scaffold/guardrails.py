"""
PE6201 · A2 scaffold — THE GUARDRAIL LAYER  (D3a)
====================================================================
Seven things, and NONE of them involve a model. That is the point.

    1. STEP CAP            stop after N turns
    2. BUDGET CEILING (tokens)  stop after N tokens
    3. ACTION DE-DUPLICATION   stop repeating an action already taken
    4. AUTONOMY GATE       hold the irreversible step for a human
    5. BUDGET CEILING (US$)    stop after N dollars                    - Harry, D3(b) #11
    6. ALREADY DECIDED     refuse a second decision on one claim       - Harry, D3(b) #8
    7. EVIDENCE CHECK      recompute the record before it is written   - Harry, D3(b) #1-3, #10

A model cannot influence whether these fire, which is why D3(b)'s
guardrail cases run on the SCRIPTED backend. They test your code.

MAKE THE STOP LOUD. A cap that silently returns an empty answer is
worse than the loop it prevented: it turns a visible cost problem into
an invisible correctness problem. Every stop below records WHY.

WHY 5-7 NEED NO CHANGE TO agent.py
    agent.py already calls guards.check_duplicate(tool, args) for every
    tool call, and guards.gate(action_name, payload, approve) once, right
    before the irreversible step. Guards 6 and 7 hook into that SAME call
    to gate() - they read payload (already passed) and self.calls_log
    (already being built for de-duplication), and 7 re-derives the answer
    itself from tools.py rather than trusting anything the agent claims.
    Guard 5 is the one exception: a live US$ ceiling needs a per-turn
    running cost. `agent.py` now computes that estimate after each model
    response and calls check_cost() before the next tool action. The hook
    was added during final assembly after the frozen live experiment, so it
    protects the submitted code without revising those reported results.
====================================================================
"""

import tools


class GuardrailStop(Exception):
    """Raised when the code layer halts a run. Carries the reason so the
    decision record can say what stopped it and at which turn."""

    def __init__(self, reason, detail=""):
        self.reason = reason
        self.detail = detail
        super().__init__("%s: %s" % (reason, detail) if detail else reason)


class Guardrails:
    """One instance per run. Never share one between cases - a shared
    instance leaks state and D4 requires every case to start clean."""

    def __init__(self, max_turns, max_tokens, autonomy,
                 max_cost_usd=None, decided_ids=None):
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self.autonomy = autonomy
        self.max_cost_usd = max_cost_usd      # None = guard 5 not armed
        self.decided_ids = decided_ids or set()  # claim_ids already decided
        self.seen_actions = set()     # signatures, for de-duplication
        self.calls_log = []           # [(tool, args_dict), ...] every call this run
        self.fired = []               # every guardrail event, for the record

    # ---- 1 · step cap -----------------------------------------------
    def check_turns(self, turn):
        if turn > self.max_turns:
            self._fire("step_cap", "reached %d turns" % self.max_turns)
            raise GuardrailStop("step_cap",
                                "hit the %d-turn cap without a conclusion"
                                % self.max_turns)

    # ---- 2 · budget ceiling -----------------------------------------
    def check_budget(self, tokens_so_far):
        if tokens_so_far > self.max_tokens:
            self._fire("budget_ceiling", "%d tokens" % tokens_so_far)
            raise GuardrailStop("budget_ceiling",
                                "spent %d tokens, ceiling is %d"
                                % (tokens_so_far, self.max_tokens))

    # ---- 3 · action de-duplication ----------------------------------
    def check_duplicate(self, tool, args):
        """A loop has no memory of its own actions unless you give it one.

        This IS that memory. Class 4's loop failure was exactly this
        guard deleted: 8 turns, no answer, 1.6x the cost, and NO
        exception raised. It did not crash. It burned money in a circle.
        """
        signature = (tool, repr(sorted(args.items())))
        if signature in self.seen_actions:
            self._fire("duplicate_action", "%s repeated" % tool)
            raise GuardrailStop("duplicate_action",
                                "%s called again with identical arguments "
                                "- the loop is not progressing" % tool)
        self.seen_actions.add(signature)
        self.calls_log.append((tool, dict(args)))   # feeds check_evidence

    # ---- 5 · budget ceiling, US$ -------------------------------------
    def check_cost(self, cost_usd):
        """Same shape as check_budget, priced in dollars rather than
        tokens. `agent.py` passes the running estimate after each model
        response, before it accepts another tool action."""
        if self.max_cost_usd is not None and cost_usd > self.max_cost_usd:
            self._fire("cost_ceiling", "US$%.5f" % cost_usd)
            raise GuardrailStop("cost_ceiling",
                                "spent US$%.5f, ceiling is US$%.5f"
                                % (cost_usd, self.max_cost_usd))

    # ---- 6 & 7 run inside the gate, BEFORE autonomy is even asked ----
    # A human should never be asked to approve a record the evidence does
    # not support - see D3(b) case ordering.
    def _check_already_decided(self, claim_id):
        if claim_id in self.decided_ids:
            self._fire("already_decided", "%s has a decision on file" % claim_id)
            raise GuardrailStop("already_decided",
                                "%s already has a decision on file - "
                                "refusing a second one" % claim_id)

    def check_evidence(self, action_name, payload):
        """Problem A only. Re-derives the correct answer from tools.py -
        the SAME data any tool call would return - and compares it with
        what the agent is trying to write. Never reads the narrative, so
        it cannot be argued out of its check in any wording or language.

        TWO SEPARATE FAILURES, because one check does not catch both:
          (a) PROCESS - the required tool calls never happened this run.
              Catches an agent that skips checks because a narrative told
              it to (CLM-9304): the line may well be genuinely payable, so
              a totals-only check would miss this. Reads self.calls_log,
              which check_duplicate has been building all run.
          (b) TOTALS - the required calls happened, but the number being
              written does not match what they said. Catches an agent
              that approves an excluded line (CLM-8941) or is asked to
              write a fabricated total (CLM-9305).
        """
        if action_name != "issue_decision_letter":
            return
        claim_id = payload.get("claim_id")
        claim = tools.get_claim(claim_id)
        if claim is None:
            return   # not this guard's job - a broken id is a data problem

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
            needed = cov.get("required_document")
            if needed and needed not in set(claim.get("documents") or []):
                continue      # the subject of an ask, not a settled line
            if cov["requires_preauth"]:
                if code not in preauth_calls:
                    missing.append("no pre-authorisation check for line %s" % code)
                    continue
                pa = tools.get_preauthorisation(claim["member_id"], code,
                                                claim["date_of_service"])
                if pa is not None:
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

    # ---- 4 · autonomy gate ------------------------------------------
    def gate(self, action_name, payload, approve=None):
        """Called ONLY in front of the irreversible step.

        Note where this sits: in front of the ACTION, not in front of the
        agent. An agent gated as a whole is not an agent, it is a form.

        Order matters: already-decided and evidence are checked BEFORE
        autonomy, so a human is never asked to approve a write that
        should never reach them at all.

        `approve` is a callable the harness supplies. On the scripted
        backend it auto-approves so the run is deterministic - and the
        record still shows the gate was passed, which is what a marker
        checks for.
        """
        if action_name == "issue_decision_letter":
            self._check_already_decided(payload.get("claim_id"))
            self.check_evidence(action_name, payload)

        if self.autonomy == "act":
            self._fire("gate_passed", "%s (autonomy=act)" % action_name)
            return True
        if self.autonomy == "suggest":
            self._fire("gate_held", "%s (autonomy=suggest)" % action_name)
            return False
        # confirm
        ok = bool(approve and approve(action_name, payload))
        self._fire("gate_%s" % ("passed" if ok else "held"),
                   "%s (autonomy=confirm)" % action_name)
        return ok

    # ---- bookkeeping ------------------------------------------------
    def _fire(self, kind, detail):
        self.fired.append({"guardrail": kind, "detail": detail})
