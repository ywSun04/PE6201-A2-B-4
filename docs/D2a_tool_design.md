# D2 · The tool layer — Problem A

Owner: Sun Yawen. Covers **D2(a)** the tool set and **D2(b)** the descriptors, the
poka-yoke moves, and the measured v1→v2 rewrite. D2(c), parallel calls, belongs to
whoever owns the loop and is not argued here.

Every number in this document was produced by a script in `docs/evidence/` and can be
re-run. Where a number is not in yet, it says so rather than being estimated.

| Claim | Script |
|---|---|
| which cases turn on which tool, and what each descriptor costs | `docs/evidence/score_tool_set.py` |
| tokens returned per call, v1 against v2 | `docs/evidence/measure_return_sizes.py` |
| all seven tools carry the brief's six fields | `docs/evidence/verify_descriptor_contract.py` |
| every poka-yoke refuses what it is meant to refuse | `docs/evidence/verify_pokayoke.py` |
| `required_documents.json` was unreachable in v1 and is reachable in v2 | `docs/evidence/probe_tool_reachability.py` |
| the four new ASK cases are derivable from the tools | `docs/evidence/verify_ask_cases.py` |
| the `check_evidence` gap, before and after | `docs/evidence/verify_evidence_guard_gap.py` — arrives with [#3](https://github.com/ywSun04/PE6201-A2-B-4/pull/3) |

---

## 1 · The data, and which tool reaches it

Problem A ships **eight** JSON files. A tool reads one thing and returns one fact, so the
first question is whether every file is reachable at all.

```
claims.json ──────────────► get_claim            the entry point; nothing runs without it
   │
   ├── member_id ─────────► lookup_policy        members.json ⋈ policies.json, joined
   │                                             inside the tool so the model never
   │                                             has to know the join exists
   │
   ├── hospital_id ───────► lookup_hospital      hospitals.json
   │
   ├── date_of_service ┐
   │                   ├──► get_preauthorisation preauthorisations.json
   ├── lines[].code ───┤    matched on all three, valid_from..valid_to inclusive
   │                   │
   │                   └──► check_coverage       procedures.json
   │                                             ⋈ policies.exclusions
   │                                             ⋈ required_documents.json   ← v2 only
   │
   └── (member, hospital, date, lines) ─► check_duplicate_claim   decided_claims.json
```

`lookup_policy` joins two files behind one call. That is deliberate and it is the brief's
**move 2** — a member is never interesting on their own in this task, only the policy
behind them, so returning both from one call removes a whole class of "looked up the
member, forgot the policy" error without adding a tool.

### The file nothing could read

`required_documents.json` was reachable by **no tool at all**. It is small — three
records — which is exactly why it went unnoticed.

The consequence was not cosmetic. `CLM-8901` ships with the assignment, its expected
decision is `request_document`, and the key demands the agent name *"itemised bill for
line 45378"*. No tool returned that string, so **no model could have decided that case
correctly**, at any temperature, with any prompt. The whole `required_document_absent`
family was unwinnable, and it would have read in the results table as a model weakness.

This is a tool-set defect, not a prompt defect, and no amount of descriptor rewriting
would have touched it. `probe_tool_reachability.py` runs both arms and shows the fact
arriving in v2 and absent in v1.

---

## 2 · The three questions

Scored over the 25 cases currently in the set. Questions 1 and 3 are measured by
`score_tool_set.py`; question 2 is judgement and is argued below the table.

The brief names a **minimum tool set** for Problem A: `get_claim`, `lookup_policy`,
`check_coverage`, `get_preauthorisation`, `get_hospital_status`, `issue_decision_letter`.
The scaffold ships those six plus `check_duplicate_claim` — so the seventh tool is the
one that has to earn its place out loud.

| Tool | 1 · Fails without it? | 2 · Confusable? | 3 · Cost when never called | Verdict |
|---|---|---|---|---|
| `get_claim` | **25 of 25.** Nothing resolves a case id | No | 340 tok/turn | The entry point |
| `check_coverage` | **25 of 25.** Every line needs its own answer | No | 411 tok/turn | The tool that does the actual work |
| `lookup_policy` | **21 of 25.** Status, dates, limit and exclusions all live here | No | 260 tok/turn | Four facts, one call |
| `issue_decision_letter` | **13 of 25** — the non-escalating ones | No | 401 tok/turn | The only write. One gate covers the agent |
| `get_preauthorisation` | **7 of 25.** Nothing else knows an approval exists | Slightly — see below | 295 tok/turn | 42 tok per case it decides |
| `lookup_hospital` | **1 of 25** — CLM-8874 alone | No | 170 tok/turn | 170 tok per case it decides |
| `check_duplicate_claim` | **1 of 25** — CLM-8933 alone | **Yes — demonstrably** | 299 tok/turn | **Our `search_notes`.** See 2.2 |

Total prefix carried by descriptors: **2176 tokens**, re-sent on every turn of every run.

### 2.1 · Question 2, where it actually bites

Only one pair in this set is genuinely confusable, and it is not two tools — it is one
tool and one argument.

`check_duplicate_claim` matches on **four facts**: member, hospital, date, and the line
list. The obvious-looking call is `check_duplicate_claim(claim_id=...)`, and it is
obvious precisely because every other tool in the set takes an id. It is also always
wrong: a resubmission arrives with a **new** claim id, so matching on the id finds
nothing and reports "not a duplicate" about a claim that is one.

That is a discriminability failure the model cannot reason its way out of from a type
signature, so it is handled in section 4 as a poka-yoke rather than as prose in a
descriptor.

`get_preauthorisation` and `check_coverage` are mildly confusable in the other direction
— both are "about a procedure code". The line that separates them is in both descriptors
and is one sentence: **coverage says whether an approval is needed, preauth says whether
one exists.** The dependency is stated as well, since calling preauth for a line that
never required one is pure waste.

### 2.2 · Which tool comes out looking like `search_notes`

`check_duplicate_claim`, on three counts:

1. **It is the one tool beyond the brief's stated minimum set.**
2. **It has the worst yield in the set** — 299 prefix tokens a turn to decide exactly one
   case out of 25. `lookup_hospital` also decides one case, but does it for 170.
3. **It is the only tool with a demonstrated confusability problem** — the `claim_id`
   call above, which fails silently in the direction that passes a duplicate through.

Where it differs from `search_notes` is question 1: it does not fail it. `CLM-8933` is
genuinely undecidable without the fact, and the brief lists *"a duplicate of a claim
already decided"* among the required negative-case families. So the tool cannot simply be
cut.

**But it fails the four-moves test, and that is the more interesting finding.** Move 3 —
*move the step out of the loop into ordinary code* — applies cleanly:

- the check needs **no model judgement**; it is an exact match on four fields the claim
  already carries;
- run **before** the agent starts, a duplicate short-circuits and the model is never
  invoked, so the case costs approximately nothing instead of a full run;
- 299 tokens leave the prefix of **every turn of every run**, including the 24 cases out
  of 25 where the tool is irrelevant;
- and the `claim_id` error class disappears entirely, because ordinary code does not have
  to guess which fields to match on.

Harry's `_check_already_decided` guard already performs a version of this at the gate,
which is evidence the fact does not need to be a tool to be enforced.

**It has not been moved**, and the reason is scheduling, not design: the five live model
runs were about to start, and changing the tool set underneath them would have made the
five v2 runs non-comparable. It is recorded here as the change this analysis would make
with more runway, with the measured saving attached — 299 tokens × every turn × every
run, against one case.

---

## 3 · The four moves — which were tried

The brief asks for this in order of preference, and asks which we tried.

| Move | Where it was used |
|---|---|
| **1 · Widen an existing tool's parameters** | Not needed. No tool in this set had a sibling worth folding in. |
| **2 · Return more from one call** | **Twice.** `lookup_policy` returns member ⋈ policy ⋈ remaining limit from one call. `check_coverage` gained `required_document` — see 3.1. |
| **3 · Move the step out of the loop** | **Identified and argued for `check_duplicate_claim` (2.2), not executed.** Reason and measured saving both recorded. |
| **4 · Add the tool** | **Not used.** No tool was added to the set. |

### 3.1 · The tool we did not add

When `required_documents.json` turned out to be unreachable, the obvious repair was an
eighth tool — `check_required_documents(code, policy_id)`. Instead the fact became a
field on a call the agent was already making.

`score_tool_set.py` measures both, using a real descriptor for the tool that was not
added, written to the same standard as the seven that shipped:

| | Descriptor cost | Cost per pass over the set | Extra calls |
|---|---|---|---|
| **Move 4** — ship the tool | 197 tok, re-sent every turn | 197 × 4 turns × 25 cases × 3 trials = **59,100 tok** | one per line |
| **Move 2** — return more | 0 — the tool was already there | measured over 41 calls = **315 tok** | none |

**About 188×, for the same fact.** The asymmetry is not really about the 7 tokens the
field adds to a coverage call. It is that a descriptor is charged on every turn of every
run whether or not the case involves a document at all, while a field is charged only on
the calls that were happening anyway.

This is the clearest thing measured in D2. A tool you do not add costs nothing forever.

---

## 4 · Poka-yoke

The brief asks for at least two, and for what each makes **impossible** rather than what
it discourages. Five shipped. All five are verified by `verify_pokayoke.py`, which calls
each one wrongly and checks the refusal — currently **9 of 9**.

| # | Before | After | What it makes impossible |
|---|---|---|---|
| 1 | `check_coverage` returns `None` for an unknown code | raises `UnknownCode`, naming the code | An invented procedure code reading as "not covered". One `None` used to mean three different things: not covered, not found, and not asked properly |
| 2 | `check_coverage` returns `None` for an unknown policy | raises `UnknownPolicy`, naming the policy | Deciding a claim against a policy that does not exist |
| 3 | `tools.call` raises a bare `KeyError` on an unknown tool name | raises `UnknownTool` | One hallucinated tool name ending a whole `--all` run instead of failing one case |
| 4 | `check_duplicate_claim(claim_id=...)` was accepted by the dispatcher | raises `UnknownArguments` with the domain reason | Matching a resubmission on an id that by definition differs from the original — silently passing a duplicate |
| 5 | `issue_decision_letter(decision: str, lines_resolved: int)` | `decision: Literal[...]`, and `lines_resolved` compared against the claim | Writing an **irreversible** record with a decision the code check cannot grade, or recording a claim as decided having resolved fewer lines than it has |

Numbers 1 and 2 close gaps 9 and 12 in `guardrail_checklist.md`, found by Harry while
testing the guard layer.

Number 5 is on the one call in Problem A that cannot be walked back, and is the brief's
own worked example — `site: str` becoming `site: Literal[...]`. Note the second half: the
tool **re-reads the claim** rather than trusting `lines_resolved`. Stating the count only
made under-counting visible; comparing it makes under-counting impossible. Same reasoning
as the evidence guard re-deriving totals instead of believing them.

All five raise subclasses of one base class, `tools.ToolError`, so the loop can catch one
thing and turn any of them into a single failed record rather than a dead run.

### What this cost elsewhere

Adding `required_document` to `check_coverage` broke `check_evidence`, which counted a
line awaiting a document as payable and so escalated correct `request_document` answers.

Worth stating plainly, because it is the kind of interaction this deliverable is supposed
to surface: `check_evidence` is reached from `gate()`, which sits in front of
`issue_decision_letter` on **every backend**. The bug would have fired for all five v2
runs and the v1 run alike, on about 16% of the set, and in the D5(b) table it would have
looked like a model weakness rather than a guard defect.

Reproduced in `verify_evidence_guard_gap.py`, which holds a frozen copy of the guard as
it was and runs both: **1 of 5 correct before, 5 of 5 after**, with CLM-9403 as the
control. The three-line fix is open for review in
[#3](https://github.com/ywSun04/PE6201-A2-B-4/pull/3) and is not on `main` yet.

---

## 5 · D2(b) · The measured rewrite

One tool, two versions of its descriptor **and its return shape**: `check_coverage`.

v1 is frozen in `descriptors_v1.py` and selected with `config.PROMPT_VERSION`. It is a
plausible first draft, not a strawman — it names the arguments and the return shape, and
what it omits is what a first draft omits: it does not say a null is ambiguous, does not
say the call is per-line, and does not carry `required_document` at all.

### What changed

| | v1 | v2 |
|---|---|---|
| Return shape | 5 fields | 6 — `required_document` added |
| Unknown code or policy | returns `None` | raises, naming what was not found |
| Six-field contract | 3 of 6 — no signature, no size bound, no irreversibility | 6 of 6, verified |
| Per-line dependency stated | no | yes |
| Whole-prompt prefix | ~980 tok | ~2570 tok |

### The three numbers

| Metric | v1 | v2 | Status |
|---|---|---|---|
| **Tokens returned per call** | mean 32.7, max 38 | mean 40.4, max 45 | **Measured.** +24% per call; 315 tokens over the 41 calls a pass makes |
| **Evaluation pass rate** | — | — | Not this file. A v1/v2 pair has to hold the model fixed. |
| **Guardrail cases passed** | 10 of 12 (D3(b) checklist; gaps 9 and 12) | 9 of 9 (`verify_pokayoke.py`) | **Measured**, scripted. The two gaps are unknown code returning `None` and unknown tool escaping as `KeyError`. |

The prefix cost is the honest problem here: **v2 is 2.6× v1**. It is not being trimmed
before the runs, deliberately. Whether the extra prefix pays for itself is exactly what
this comparison is for, and cutting it on instinct beforehand would throw the measurement
away. If v2 loses on cost per correct decision, that goes in the report as the finding.

What is already certain is the direction of the *correctness* term: under v1 the
`required_document` family cannot be decided correctly by any model, because the fact
never reaches the loop. Whatever v1's pass rate turns out to be, that part of it is a
tool-set limit and not a model one — and the rate must be read with guardrail halts
filtered out, or a run stopped by a guard counts as a wrong answer.

---

## 6 · What is not done

- **Live numbers.** Evaluation pass rate for a matched v1/v2 pair still needs
  the same model on both arms. Guardrail cases are already measured scripted.
- **`get_preauthorisation` returns `None` for an expired approval and for a valid one
  that was never granted.** Those are different facts leading to different decisions, and
  the tool cannot currently tell them apart — the same shape of defect as poka-yoke 1,
  found late and not yet fixed. It makes `CLM-8894`'s `must_record` unreachable.
- **`check_duplicate_claim` out of the loop** (2.2) — argued and measured, not executed.
- **Problem B's descriptors** are left as the scaffold shipped them. We submit A.
