# Report · Section 2 · The tool layer

**Budget: 450 words.** Tables and figures do not count toward it, so every number below
sits in a table and the prose is spent on the argument.

This file holds the **D2(a) and D2(b)** prose — the tool set, what was cut, and what the
descriptor rewrite measured. Drafted by Sun Yawen, ~360 words.

**The last ~90 words are D2(c)** (Preethi; Problem A `CLM-8842`). D2(a) and
D2(b) below are Sun Yawen's.

The pass-rate row is the matched `openai/gpt-4o-mini` pair on the frozen
40-case / 86-trial set. Tokens returned and guardrail cases are scripted
measurements from `docs/evidence/`.

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

D2(c) – Parallel tool calling. Tool calls are grouped only when neither call requires the other call’s output; dependent or irreversible actions remain sequential. For Problem A case CLM-8842, the claim is retrieved first. Once the required inputs are available, independent policy, hospital, and coverage checks can share a turn. Pre-authorisation waits for the coverage result, while the final decision waits for the required evidence and autonomy gate. Grouping therefore completes the same eight tool calls in four model turns. The decision and supporting evidence remain unchanged, showing improved efficiency without changing correctness.

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
| Evaluation pass rate | **17 of 86** (19.8%). `openai/gpt-4o-mini`, frozen 40-case set, prompt v1. Liu Zeyuan, `docs/evidence/live_results_liu_v1.json`. | **31 of 86** (36.0%). Same model, same 40 cases and 86 trials, prompt v2. Preethi, PR #6. |
| Guardrail cases passed | **10 of 12** on the D3(b) checklist, scripted, before the interface change. The two fails are case 9 (`check_coverage("99999", …)` returned `None`) and case 12 (unknown tool name escaped as a bare `KeyError`). | **9 of 9** in `docs/evidence/verify_pokayoke.py`, scripted. Replays those two calls plus seven further wrong ones (unknown policy, invented tool, `claim_id` as a duplicate key, partial duplicate match, bad arguments, non-enumerated decision, under-counted lines, unknown claim id). Each raises a named `ToolError`. |

Tokens returned and guardrail cases are scripted measurements of the tool
interface, not of a model, so they do not mix vendors. The pass-rate row is
the matched live pair: same model, same 40 cases and 86 trials, descriptors
the only change (Liu v1 vs Preethi v2). Do not substitute the qwen v2
battery — that run is a different model.

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
- The pass-rate row is the matched `openai/gpt-4o-mini` pair (17/86 vs 31/86).
  Do not replace either cell with the `qwen/qwen3.8-flash` battery (19 of 86):
  that run is a different model. These are automated code-check rates, not
  human judgement.
