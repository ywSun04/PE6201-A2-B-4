# PE6201 Assignment 2 — Problem A Final Report

**Team:** B-4  
**Problem:** A — Claims Triage Agent  
**Repository and reproducibility evidence:** `A2_scaffold/`, `docs/evidence/`, and the result ledgers linked below.

## 0. Why an agent?

Problem A is not a one-shot classification problem. A claim can only be triaged by joining evidence held in separate claim, member, policy, procedure, hospital, pre-authorisation, required-document, and earlier-decision records. What should be looked up next is conditional on what has already been found: an inactive policy can end the investigation, a covered procedure may require a valid authorisation, and a missing document can change the action. A fixed workflow would either retrieve irrelevant data for every claim or become a fragile collection of special-case branches.

We therefore use a bounded tool-using agent. Starting from a claim identifier, it retrieves only the evidence needed for that case, then returns one controlled action: `approve_in_principle`, `request_document`, or `escalate`. This is useful agency rather than unrestricted automation because it is constrained by explicit tools, finite turn and token budgets, duplicate-action protection, evidence checks, and a human confirmation gate before a decision letter can be issued. The agent records its tool calls, observations, costs, and guardrail events, making each recommendation inspectable.

## 1. Agent loop and system architecture

The implementation follows a ReAct-style loop: the model reads the current claim state, proposes one or more tool calls, receives structured observations, and repeats until it can reach a controlled conclusion. The execution layer, rather than the model alone, owns state and safety: it validates tool arguments, logs every event, deduplicates actions, applies resource limits, and checks the evidence behind a proposed result.

The central architectural choice is to separate the semantic decision from the irreversible external action. The model may recommend a disposition, but `issue_decision_letter` is allowed only after the ledger has verified the relevant records and the configured autonomy policy permits it. This keeps the live model useful for selecting evidence under uncertainty while leaving validation, auditability, and irreversible effects to deterministic code.

## 2. Tool design and parallel tool calling

We designed seven tools around information needs rather than mirroring every data file. `get_claim` establishes the case; member, policy, hospital, coverage, pre-authorisation, duplicate, and decision tools answer distinct questions that can change the disposition. Required documents are returned as a coverage field rather than exposed as an eighth independent tool, avoiding a needless call. V2 strengthens the descriptors with typed arguments, timing, outputs, prohibited uses, and bounds. For example, unknown identifiers return named errors; malformed duplicate checks are rejected; and the final action is validated against the accumulated record.

Some calls are independent after the claim is known, whereas others depend on an earlier result. The agent may therefore group independent lookups in one model turn, but must preserve order for dependencies such as checking a pre-authorisation only after coverage says it is needed. Our deterministic scheduling control verifies this rule across the full frozen set: grouped and sequential schedules produced identical decisions and evidence order, while grouping reduced the number of model turns. The figures in the linked ledger are transcript estimates, not vendor billing tokens; the control deliberately raises normal safety caps only to isolate scheduling from semantic behaviour.

| Full-set deterministic control | Sequential | Grouped |
|---|---:|---:|
| Cases / tool calls | 40 / 218 | 40 / 218 |
| Model turns | 218 | 116 |
| Estimated transcript cost | US$0.258876 | US$0.110412 |
| Code checks | 40 / 40 | 40 / 40 |

Evidence: `docs/evidence/parallel_call_measurement.json` and `docs/evidence/measure_parallel_calls.py`.

## 3. Guardrails and verification

The agent is bounded by an eight-turn cap and a 60,000-token cap. It also rejects repeated actions, stops a second attempt to decide an already decided claim, validates proposed evidence before a letter can be issued, and uses the configured autonomy policy to hold irreversible actions for human confirmation. A per-turn dollar ceiling is wired at the execution layer, so cost enforcement does not rely on model compliance.

We verified the guards with focused, reproducible checks. A deliberately low dollar ceiling stops execution after the first paid tool call; `suggest` autonomy records a recommendation but does not issue a letter; and invalid tool requests are rejected by the Poka-yoke tests. These checks test system behaviour that ordinary accuracy metrics cannot reveal. The dollar hook was added after the frozen live batteries, so it is verified separately and does not alter their reported results.

Evidence: `docs/evidence/verify_cost_ceiling_wiring.py`, `docs/evidence/verify_autonomy_suggest.py`, and `docs/evidence/verify_pokayoke.py`.

## 4. Evaluation method and results

We froze Problem A at 40 claims and 86 trials before comparing prompts or models. Automated code checks score the final action and supporting record; a stricter human review separately checks whether the recorded explanation contains every required reasoning point. This distinction matters: a correct action can still lack the evidence needed for audit or communication. The scripted replay provides a deterministic baseline and passes all 86 trials; live batteries are retained without rerunning failed cases or cherry-picking outcomes.

The cleanest comparison is V1 versus V2 on the same `openai/gpt-4o-mini` model, frozen set, and trial mix. V2 improves the automated pass rate, but costs more and does not reduce the stricter review burden in this dataset. It should therefore be read as an improvement in executable task completion, not proof that its explanations are ready for unattended use. Other vendor results are useful integration observations, not a capability league table: Gemini and Claude encountered substantial structured-output parsing failures, so their totals also measure compatibility with this harness.

| Live battery | Prompt / model | Automated code checks | Total model cost | Interpretation |
|---|---|---:|---:|---|
| Liu | V1 / gpt-4o-mini | 17 / 86 (19.8%) | US$0.065094 | Matched baseline |
| Preethi | V2 / gpt-4o-mini | 31 / 86 (36.0%) | US$0.122829 | Matched V1/V2 comparison |
| Sun | V2 / qwen3.8-flash | 19 / 86 (22.1%) | US$0.153983 | Descriptive cross-model result |
| Kou | V2 / Mistral | 6 / 86 (7.0%) | US$0.042586 | Descriptive cross-model result |
| Harry | V2 / Gemini | 8 / 86 (9.3%) | US$1.037978 | 68 parse fallbacks |
| Iris | V2 / Claude | 0 / 86 | US$0.655554 | 86 parse fallbacks after claim retrieval |

The V1 human review found 1 of 40 explanations complete; the V2 review found 0 of 40 complete. Review records, transcripts, and full numbers are in `docs/evidence/live_results_liu_v1.json`, `Preethi_gpt-4o-mini_v2_40cases_combined_results.json`, `docs/evidence/live_results.json`, `docs/evidence/live_results_kou_v2.json`, and `docs/evidence/live_results_harry.json`.

## 5. Two reproduced failures

The first reproduced failure removes action de-duplication. On an expired pre-authorisation case, the agent continues revisiting the same action instead of making progress. The final disposition remains correct, but the run expands from four to six turns and consumes substantially more tokens without triggering the ordinary caps. This demonstrates why final-action accuracy is inadequate as the only success measure: a system can be right yet unnecessarily expensive and unstable.

The second failure removes the computed remaining policy limit. For CLM-9302, the annual limit looks sufficient when viewed alone, but earlier approved claims have already consumed most of it. Without the computed remainder, the agent approves a claim that should be escalated. This is a tool-interface defect, not simply a poor prompt: the necessary fact was not made available in the form required for a correct decision. Both reproductions show why guardrails and tool semantics must be evaluated alongside model output.

Evidence: `docs/report_section5.md` and the reproduced-failure scripts referenced there.

## 6. Cost to serve and conclusion

Cost to serve has three layers: model inference, platform operation, and human exception handling. The prototype's local JSON data means platform cost is not yet representative of production, where storage, network, monitoring, and security controls would be added. The matched V1/V2 result shows V2's higher inference cost buys more automated code-check passes. If every avoided automated failure would otherwise require human review, the illustrative break-even threshold is US$0.00412 per avoided review.

That threshold is conditional, not a production saving claim. Strict human review found neither prompt reliably records all required reasoning points, and V2 did not show a lower reasoning-review burden. Until independent reviewers confirm that explanation quality and exception workload improve, human review remains part of the service design. Our conclusion is therefore limited: bounded tool use, explicit validation, and parallel scheduling make the system more controllable and more efficient than an unstructured workflow, but live deployment requires stronger structured-output handling and evidence-complete explanations.

Evidence and calculations: `docs/report_section6.md`, `docs/evidence/live_results_liu_v1.json`, and `Preethi_gpt-4o-mini_v2_40cases_combined_results.json`.

## Limitations

The deterministic scheduler estimates cannot be compared directly with vendor token bills. Cross-vendor live results confound model behaviour with structured-output compatibility. Automated code checks verify the proposed record, not the completeness of written reasoning. Finally, the V2 strict review was completed during final integration rather than by an independent reviewer; the raw V2 results were not changed. These constraints motivate the conservative conclusions above.
