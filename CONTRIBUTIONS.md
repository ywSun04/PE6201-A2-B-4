# Contributions

Per member, per the Team Declaration's strand assignments (section 4). Each person fills
in their own row — that is what makes this corroborate the commit history rather than
restate it. `git log --author="<github-username>"` reproduces every row below.

| # | Name | GitHub | Strand(s) owned | Summary |
|---|---|---|---|---|
| 1 | Sun Yawen | ywSun04 | D2(a), D2(b) — tool design, descriptors, v1/v2 rewrite | *fill in* |
| 2 | Chan Hio Weng (Harry) | harry00001177 | D3, D7 — guardrails and two reproduced failures | see below |
| 3 | Liu Zeyuan | Lizzy-808 | D0, D6, D5(b) v1 — cost model, v1 battery, report/video | *fill in* |
| 4 | Mohanarangan Preethi | preethi1522 | D1, D2(c) — agent loop, tool implementation, parallel calls | *fill in* |
| 5 | Zhang Yizhuo | waterrrr0924 | D4, D5(a) — evaluation harness, scripted run | *fill in* |
| 6 | Kou Huilin | khl789 | D4 (data) — fixtures, extra cases, answer key | *fill in* |

## 2 — Chan Hio Weng (Harry) — D3, D7

**Guardrails (`A2_scaffold/guardrails.py`).** Added three guards beyond the scaffold's
four: an evidence check that re-derives the payable total from `tools.py` before
`issue_decision_letter` fires (catches record tampering and skipped checks, not just
wording), an already-decided check, and a US$ cost ceiling (logic verified standalone;
wiring a live per-turn call is Preethi's, in `agent.py`, on her review). All three hook
into the existing `gate()` call — no change to `agent.py` was needed for two of the three.

**D3(b) checklist (`guardrail_checklist.md`).** 12 cases designed and run on the scripted
backend: 10 pass; 2 confirm gaps in `tools.py`/`agent.py` (unknown procedure code, unknown
tool name) that were reported to their owners rather than fixed here. Includes a signal-only
run of Class 6's keyword scan against the 5 hostile-narrative cases (1 of 5 flagged),
supporting the case for a structural guard over text filtering.

**D7 — two reproduced failures** (`A2_scaffold/demo_loop_failure.py`,
`demo_tool_interface_failure.py`). Failure 1: action de-duplication deleted, agent circles
on an expired pre-authorisation — no crash, same right answer, 1.7x the cost; neither the
step cap nor the token ceiling catches it at current limits. Failure 2: `lookup_policy`'s
computed `remaining` field deleted, agent reads the raw annual limit and wrongly approves a
claim that is actually over its real remaining headroom; invisible to every D3(a) guard, so
the fix belongs at the interface, not in loop control or the prompt.

**6 evaluation cases** (CLM-9301-9306): 3 rule-based escalates, 3 hostile-narrative
escalates, all labelled from Appendix A's routing table before any run, scripted and
passing the code check.

**Report:** drafted section 5 (`docs/report_section5.md`).

**Commits** (`git log --author=harry00001177`): `b90b2bd`, `6d5bb96`, `97977d9`, `eb2de02`,
`7edd380`, `2c9a06c`, `85d0870`, plus review and merge of PR #3
(`syw-fix-evidence-guard`, Sun Yawen's fix to a gap in the evidence check she found while
adding the `required_document` field).
