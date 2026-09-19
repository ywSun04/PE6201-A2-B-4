# Contributions

Per member, per the Team Declaration's strand assignments (section 4). Each person fills
in their own row — that is what makes this corroborate the commit history rather than
restate it. `git log --author="<github-username>"` reproduces every row below.

**AI tools.** Brief section 6, condition 3: sources and tools used are attributed. If you
used an AI coding assistant for your strand, name it and how in your own section below —
see #2 for the shape.

| # | Name | GitHub | Strand(s) owned | Summary |
|---|---|---|---|---|
| 1 | Sun Yawen | ywSun04 | D2(a), D2(b) — tool design, descriptors, v1/v2 rewrite | see below |
| 2 | Chan Hio Weng (Harry) | harry00001177 | D3, D7 — guardrails and two reproduced failures | see below |
| 3 | Liu Zeyuan | Lizzy-808 | D0, D6, D5(b) v1 — cost model, v1 battery, report/video | *fill in* |
| 4 | Mohanarangan Preethi | preethi1522 | D1, D2(c) — agent loop, tool implementation, parallel calls | *fill in* |
| 5 | Zhang Yizhuo | waterrrr0924 | D4, D5(a) — evaluation harness, scripted run | *fill in* |
| 6 | Kou Huilin | khl789 | D4 (data), D5(b) — fixtures, answer key, Mistral live battery | see below |
## 1 — Sun Yawen — D2(a), D2(b)

**AI tools used:** Cursor (Grok 4.6) as a coding assistant for the tool layer,
descriptors, evidence scripts, and this write-up. Commits on `main` are authored
only as `ywSun04` — the brief grades contribution from history, so assistant
trailers were stripped rather than left on the record. Design decisions (which
file was unreachable, which tool is this set's `search_notes`, returning
`required_document` as a field instead of an eighth tool, the five poka-yoke
moves, not changing the tool set once live runs were pending) were mine; every
number below was re-run from `docs/evidence/` before it was quoted.

**Tool set (`A2_scaffold/tools.py`, `docs/D2a_tool_design.md`).** Scored the seven
Problem A tools against the brief's three questions. `required_documents.json` was
reachable by no tool; `check_coverage` now returns that field (move 2, not an
eighth tool). `check_duplicate_claim` is the weakest yield in the set and the one
tool beyond the brief's minimum — argued for moving out of the loop (move 3), not
executed because five live runs were about to start. Five poka-yoke: unknown
code/policy/tool raise named `ToolError`s; `check_duplicate_claim` refuses
`claim_id`; `issue_decision_letter` enumerates `decision` and re-reads the claim
to check `lines_resolved`.

**Descriptors.** v2 carries the brief's six fields (typed signature, bad-value
behaviour, measured size bound, irreversibility). v1 is frozen in
`descriptors_v1.py`, selected with `config.PROMPT_VERSION`. Prefix ~980 tok (v1)
vs ~2570 tok (v2). `check_coverage` tokens returned per call: mean 32.7 → 40.4.

**PR #3** (`syw-fix-evidence-guard`): `check_evidence` counted a line awaiting a
document as payable and would have wrongly escalated ~16% of the set on every
backend. Three lines, merged by Harry after he re-ran the reproduction.

**4 ASK cases** (CLM-9401–9404) plus scripts for CLM-8901.

**Live battery (D5(b), this member's model).** `qwen/qwen3.8-flash`, v2, 25 cases,
63 trials: **17 of 63 code-check pass (27%)**, US$0.124. Decision agreed on 47 of
63 (75%) — most code-check fails are trigger-string mismatches. ASK family 7 of
12. Results: `docs/evidence/live_results.json`. v1 arm not yet run.

**Report:** drafted section 2 (`docs/report_section2.md`); D2(c) slot left for
the loop owner.

**Commits** (`git log --author=ywSun04`): `ea5a1d5`, `80c3213`, `7ac6b19`,
`0ee20b1`, `74fa077`, `4ec8659`, `137ffa3`, `4154e8b`, `45ed266`, `8c498ec`,
`7249421`, `c742146`, `36dcf98`, plus PR #3.

## 2 — Chan Hio Weng (Harry) — D3, D7

**AI tools used:** Claude Code (Anthropic), as a coding assistant throughout D3/D7 -
guardrail design, the two reproduced-failure demos, and this report section. Every commit
below carries a `Co-Authored-By: Claude` trailer for the same reason, visible in the
commit history GitHub renders. I can explain every block I submitted; the design
decisions (which guard catches which attack, why failure 2 sits at the interface, the
`check_evidence`/`check_duplicate` coupling bug found and fixed while building failure 1)
were mine, argued through and verified by re-running the code before each one landed.

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

## 6 — Kou Huilin — D4 (data), D5(b)

**AI tools used:** ChatGPT/Codex was used to help interpret the repository instructions, prepare the member-specific live-battery runner, inspect errors, and guide validation. I executed the commands and OpenRouter run myself, checked the generated files, and manually graded all 40 judgement-queue entries against the pre-written `must_record` requirements.

**Evaluation cases (D4).** Added four duplicates/history cases, CLM-9601–CLM-9604: one true duplicate and three near misses differing respectively by member, hospital, and line amount. Added the matching history rows CLM-9591–CLM-9594 to `EXTRA_DECIDED`, consolidated the cases into `EXTRA_CLAIMS`, and added their hand-written labels to `expected_outcomes_A.json`. These changes were merged in PR #4. The final Problem A set contains 40 cases, and `check_my_data.py` reports that the data hangs together.

**Live battery (D5(b)).** Ran `mistralai/mistral-small-3.2-24b-instruct` through OpenRouter with the shared v2 prompt and the final 40-case evaluation set. Negative cases received three trials and ordinary ACT cases one trial, producing 86 trials in total. The automated code check passed 6 of 86 trials (6.98%); median tool-calling turns were 2, and the runner recorded US$0.042586. The run contained 71 `unknown_policy_id` stops and 9 captured live-call/harness failures: five `ValueError: too many values to unpack (expected 2)` and four `AttributeError: 'str' object has no attribute 'items'`. These observed failures were retained without changing the shared prompt, data, or answer key to suit this model.

**Judgement check.** I manually reviewed one judgement entry for each of the 40 cases against its pre-written `must_record` requirements. None of the recorded reasons satisfied every required item, so the judgement result was 0 of 40. Some trials passed the automated decision/trigger check but had no written reason, so they did not pass the independent judgement check.

**Artefacts:** `docs/evidence/run_live_battery_kou.py` and `docs/evidence/live_results_kou_v2.json`.