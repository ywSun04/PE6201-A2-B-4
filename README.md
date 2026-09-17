# PE6201-A2-B-4

PE6201 A2 · Problem A — the claims triage agent.

## Running it

Everything below runs on the **scripted backend**: no API key, no network, no cost, and
the same answer every time.

```
python3 A2_scaffold/run_eval.py             # the scripted cases
python3 A2_reference_data/check_my_data.py  # the data still hangs together
```

`config.py` holds the switches. `PROMPT_VERSION` selects the v1 or the v2 descriptor set
and must be `v1` only for the D2(b) baseline run.

## Deliverable write-ups

| | Document | Owner |
|---|---|---|
| D2(a), D2(b) | [`docs/D2a_tool_design.md`](docs/D2a_tool_design.md) — the tool set, the three questions, poka-yoke, the v1→v2 rewrite | Sun Yawen |
| D3(b) | [`guardrail_checklist.md`](guardrail_checklist.md) — the guard layer and its cases | Harry (CHAN HIO WENG) |

## Evidence

`docs/evidence/` holds the scripts behind the numbers in those write-ups. Each one is
standalone, prints what it checked, and exits non-zero if the claim it makes stops being
true — so they double as regression tests.

```
score_tool_set.py               which cases turn on which tool, what each descriptor costs
measure_return_sizes.py         tokens returned per call, per tool, v1 against v2
verify_descriptor_contract.py   every tool carries the brief's six fields
verify_pokayoke.py              every poka-yoke refuses what it should
probe_tool_reachability.py      required_documents.json: unreachable in v1, reachable in v2
verify_ask_cases.py             the four ASK cases are derivable from the tools
```
