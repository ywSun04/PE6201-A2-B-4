# Report · Section 2 · The tool layer

**Budget: 450 words.** Tables and figures do not count toward it, so every number below
sits in a table and the prose is spent on the argument.

This file holds the **D2(a) and D2(b)** prose — the tool set, what was cut, and what the
descriptor rewrite measured. Drafted by Sun Yawen, ~360 words.

**The last ~90 words belong to D2(c)** — the dependency rule and what parallel calling
saved — and are marked with a placeholder for whoever owns the loop. Section 2 cannot be
handed to the report editor until that slot is filled.

Numbers marked **[LIVE]** are waiting on the model battery. Everything else is measured
and reproducible from `docs/evidence/`.

---

## Draft

### 2 · The tool layer

**Why this set.** Problem A's minimum is six tools; the scaffold ships a seventh,
`check_duplicate_claim`. Scored against the three questions over 25 cases it is our
`search_notes`: 299 prefix tokens re-sent every turn to decide one case, the worst yield
in the set, and the only tool with a demonstrated confusability failure — models call it
with `claim_id`, which is always wrong, because a resubmission arrives with a new one. It
passes question 1 nonetheless: CLM-8933 is undecidable without the fact. What it fails is
the four-moves test. An exact match on four fields needs no model judgement, so move 3
applies — run it before the agent starts, and a duplicate short-circuits while 299 tokens
leave every turn of every run. We measured that and did not execute it, because changing
the tool set with five live runs pending would have made those runs non-comparable.

**What we cut is a tool we never added.** `required_documents.json` was reachable by no
tool, which made CLM-8901's labelled `request_document` unattainable for any model at any
temperature — a tool-set defect no prompt could reach. The obvious repair was an eighth
tool. Instead the fact became a field on a call already being made. Written to the
standard of the seven that shipped, that tool's descriptor costs 197 tokens re-sent every
turn against 315 measured for the field: **188×, for the same fact.** The asymmetry is
not the seven tokens per call — it is that a descriptor is billed on every turn whether
the case involves a document or not.

**What the rewrite measured.** Five poka-yoke replaced instructions to be careful with
constraints that make the error impossible: an invented code now raises instead of
returning a `None` that meant three different things, and the irreversible write refuses
a decision outside its enumeration and re-reads the claim rather than trusting the line
count it was handed. Those hold when the model changes; an instruction does not. The
honest cost is the prefix — v2 is 2.6× v1, and we did not trim it before the battery,
because whether it pays for itself is precisely what the comparison exists to measure.

> **[D2(c) — ~90 words, owner of the loop]** State the dependency rule, then what
> parallel calling saved: turns and tokens, sequential against grouped, on the same
> cases, with the pass rate alongside to show correctness did not move.

---

## The table that carries the numbers

**`check_coverage`, v1 against v2** — one tool, both its descriptor and its return shape.

| | v1 | v2 |
|---|---|---|
| Tokens returned per call | mean 32.7, max 38 | mean 40.4, max 45 |
| Whole prompt prefix | ~980 tok | ~2,570 tok |
| Six-field contract | 3 of 6 | 6 of 6 |
| Unknown code or policy | returns `None` | raises, naming it |
| `required_document` reachable | no | yes |
| Evaluation pass rate | **[LIVE — v1 not run yet]** | **17 of 63 trials (27%)** on `qwen/qwen3.8-flash`, 25 cases, 2026-09-17. Median 2 turns. See `docs/evidence/live_results.json`. Raw rate understates outcome-agreement: several escalate cases chose the right decision and failed only on the trigger string. |
| Guardrail cases passed | **[LIVE — not this battery]** | Not run on live; Harry's 12 scripted guardrail cases remain the D3(b) measurement. |

Both arms run on the same model, as the brief requires, so the difference is attributable
to the descriptor and not to the model.

**The tool set, scored** — full table with all seven tools in
[`docs/D2a_tool_design.md`](D2a_tool_design.md).

| Tool | Cases it decides, of 25 | Prefix tokens/turn |
|---|---|---|
| `get_claim` | 25 | 340 |
| `check_coverage` | 25 | 411 |
| `lookup_policy` | 21 | 260 |
| `issue_decision_letter` | 13 | 401 |
| `get_preauthorisation` | 7 | 295 |
| `lookup_hospital` | 1 | 170 |
| `check_duplicate_claim` | 1 | 299 |

---

## Notes for the editor

- **Do not cut the 188× or the 2.6×.** They are the two halves of the same argument — the
  first is what an interface constraint saves, the second is what it costs — and the
  section reads as one-sided with either one removed.
- If the section runs long, the first sentence of each paragraph carries the claim; the
  rest is support and can be compressed.
- `[LIVE]` cells must be filled before submission, and pass rates need guardrail halts
  filtered out — a run stopped by a guard is not a wrong answer and counts as one if the
  rate is taken raw.
