# Report · Section 5 · The two failures

**Budget: 250 words.** Tables and figures do not count toward it.

This file holds the **D3/D7** prose — the loop failure, how it was found, the fix and its
before/after; the second failure and why its layer. Drafted by Harry, ~245 words.

Both failures are built as deletions from the working agent (`A2_scaffold/demo_loop_failure.py`,
`A2_scaffold/demo_tool_interface_failure.py`), run on the scripted backend, reproducible with
no key. Numbers below are a fresh run against the current `main` (12 of the ~30-50 planned
cases scripted; re-run once the set is complete — the method does not change, only the count).

---

## Draft

### 5 · The two failures

**Failure 1 — loop control.** Deleting action de-duplication and feeding the agent a claim
whose pre-authorisation had expired turned a four-turn run into six: instead of asking for a
missing document, it re-queried `get_preauthorisation` with a new date each turn. Nothing
raised an exception and the decision was still correct — a pass-rate table alone would have
shown a clean pass. Per-run instrumentation (turns, tokens, cost) is what surfaced it: 1.7×
the tokens for the same answer. Neither the step cap (6 turns, cap 8) nor the token ceiling
(42,840 of 60,000) fired; both bound damage, neither detects a loop that stays inside them.
Only de-duplication, which remembers prior calls, catches this class of fault. Across the 12
cases currently scripted, removing the guard left the pass rate unchanged at 34/34 — it
protects circling runs specifically, not well-behaved ones.

**Failure 2 — tool interface.** Deleting `lookup_policy`'s computed `remaining` field forces
a comparison against the raw annual limit instead. On CLM-9302 (740 total, under the 6,000
limit but over the 600 actually remaining) this flips a correct escalate into a wrong
approve. No D3(a) guard catches it — the rule lives above the guardrail layer, in the tool —
so only an interface fix, computing the number once, closes it; a prompt reminder is paid on
every call and does not survive a rewrite. Restoring the field recovers the correct decision.
