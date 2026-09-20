# PE6201 Assignment 2 - Problem A Final Report

**Team:** B-4<br>
**Problem:** A - Claims Triage Agent<br>
**Repository evidence:** `A2_scaffold/`, `docs/evidence/`, and the ledgers linked below.

## 1. Why an agent?

Problem A is not a one-shot classification task. A claim must be triaged by joining separately stored claim, member, policy, procedure, hospital, pre-authorisation, required-document, and earlier-decision records. The next useful lookup depends on what has already been found: an inactive policy can end the run, a covered procedure can require authorisation, and a missing document can change the disposition. Crucially, these records can contradict the model at machine speed, so they provide the ground-truth signal required to supervise a loop.

We place the task on rung 7 of the Class 4 ladder. Rungs 1-6 are useful cheaper workflows, but none alone can select a varying sequence of evidence checks and then make a gated write. We move down the ladder only where the preceding rung fails.

| Rung | What it would provide for Problem A | Why it is insufficient alone |
|---|---|---|
| 1. Single call | A fixed recommendation | No access to changing systems of record |
| 2. Prompt chain | A known sequence of checks | Cannot adapt to lines, documents, or authorisation evidence |
| 3. Routing | A choice among preset paths | The next evidence request is not one of a fixed set of lanes |
| 4. Parallelisation | Faster independent lookups | Does not decide dependent next steps |
| 5. Orchestrator-workers | Specialist delegation | Adds hand-offs without resolving the shared evidence dependency |
| 6. Evaluator-optimiser | A second-pass critique | Can assess a draft, but cannot replace record-backed validation |
| 7. Agent | Runtime selection of tools and sequence | Needed here, but bounded and audited |

Our single agent therefore retrieves evidence at runtime, may group independent calls, and returns only `approve_in_principle`, `request_document`, or `escalate`. Its first irreversible action is `issue_decision_letter`; that action is protected by deterministic evidence validation and a human confirmation policy. This is an agent rather than read-only agentic retrieval because it can eventually change the record, while the write is kept outside the model's unilateral control.

Run success compounds across turns. Using the measured code-check pass rate P and median turns T, the implied per-step diagnostic is `s = P^(1/T)`. It is not a physical constant - policy lookups and free-text reasoning are not equally reliable - but it makes the cost of longer trajectories visible. With T = 3 in the matched live batteries, the V1 and V2 values are:

| Matched gpt-4o-mini battery | P | T | Implied s |
|---|---:|---:|---:|
| V1 | 17 / 86 | 3 | 0.583 |
| V2 | 31 / 86 | 3 | 0.712 |

The design therefore attacks both levers: improve evidence quality and descriptors where a step is weak, and remove only genuinely independent waiting by parallelising calls. Step and token ceilings prevent the cost of an unknown trajectory from becoming unbounded.

### Single-agent architecture

The implementation is a single-agent ReAct loop: Thought -> Action -> Observation -> repeat -> Final. The execution layer, not the model alone, owns state and safety: it validates arguments, logs events, deduplicates actions, applies budgets, and checks the evidence behind a proposed result. This separates a useful semantic recommendation from an irreversible external action and keeps the run auditable.

## 2. Tool design and parallel tool calling

We designed seven tools around information needs rather than mirroring every data file. `get_claim` establishes the case; member, policy, hospital, coverage, pre-authorisation, duplicate, and decision tools answer questions that can change the disposition. Required documents are returned as a coverage field rather than exposed as an eighth independent tool. V2 adds typed arguments, timing, outputs, prohibited uses, and bounds. Unknown identifiers return named errors, malformed duplicate checks are rejected, and the final action is validated against the accumulated record.

Calls that become independent after `get_claim` may be grouped in one model turn; calls whose inputs depend on an earlier observation remain ordered. The full-set deterministic control confirms that grouped and sequential schedules produce the same decisions and evidence order. Its figures are transcript estimates rather than vendor billing tokens, and it deliberately raises normal safety caps only to isolate scheduling.

| Full-set deterministic scheduling control | Sequential | Grouped |
|---|---:|---:|
| Cases / tool calls | 40 / 218 | 40 / 218 |
| Model turns | 218 | 116 |
| Estimated transcript cost | US$0.258876 | US$0.110412 |
| Code checks | 40 / 40 | 40 / 40 |

Evidence: `docs/evidence/parallel_call_measurement.json` and `docs/evidence/measure_parallel_calls.py`.

## 3. What the evidence showed

We froze Problem A at 40 claims and 86 trials before comparing prompts or models. Automated code checks score the final action and supporting record; strict human review separately checks whether the recorded explanation contains every required reasoning point. A correct action can therefore still be unsuitable for audit or communication. The scripted replay is the deterministic baseline and passes all 86 trials; live batteries were retained without rerunning failed cases or cherry-picking outcomes.

The cleanest experiment holds `openai/gpt-4o-mini`, the frozen set, and the trial mix constant while changing V1 to V2. V2 improves executable task completion but costs more and did not reduce strict reasoning-review failure. It is therefore not evidence that explanations are ready for unattended use. Other vendor results are integration observations, not a capability ranking: Gemini and Claude encountered structured-output parsing failures, so their totals also reflect compatibility with this harness.

| Live battery | Prompt / model | Automated code checks | Total model cost | Interpretation |
|---|---|---:|---:|---|
| Liu | V1 / gpt-4o-mini | 17 / 86 (19.8%) | US$0.065094 | Matched baseline |
| Preethi | V2 / gpt-4o-mini | 31 / 86 (36.0%) | US$0.122829 | Matched comparison |
| Sun | V2 / qwen3.8-flash | 19 / 86 (22.1%) | US$0.153983 | Cross-model observation |
| Kou | V2 / Mistral | 6 / 86 (7.0%) | US$0.042586 | Cross-model observation |
| Harry | V2 / Gemini | 8 / 86 (9.3%) | US$1.037978 | 68 parse fallbacks |
| Iris | V2 / Claude | 0 / 86 | US$0.655554 | 86 parse fallbacks after claim retrieval |

The V1 strict review found 1 of 40 explanations complete; the V2 review found 0 of 40 complete. Guardrails also matter independently of pass rate: an eight-turn cap, 60,000-token cap, action de-duplication, evidence validation, human confirmation, and a per-turn dollar ceiling are verified by focused scripts. The cost hook was added after the frozen live batteries, so it does not alter their numbers.

Evidence: `docs/evidence/live_results_liu_v1.json`, `Preethi_gpt-4o-mini_v2_40cases_combined_results.json`, `docs/evidence/live_results.json`, `docs/evidence/live_results_kou_v2.json`, `docs/evidence/live_results_harry.json`, `docs/evidence/verify_cost_ceiling_wiring.py`, `docs/evidence/verify_autonomy_suggest.py`, and `docs/evidence/verify_pokayoke.py`.

## 4. What it costs

We use the brief's declared Problem A deployment scenario: 8,000 claims per month and a US$7.60 assessor escalation cost (US$38/hour for 12 minutes). This is a stated scenario, not a measured production workload. The measured 86-trial ledger supplies the per-run inference cost and code-check pass rate. Layer 3 is US$0 only in this local-JSON prototype; production storage, network, monitoring, and maintenance remain unpriced rather than free.

| Expected cost per claim in the stated scenario | V1 | V2 |
|---|---:|---:|
| Layer 1: metered model cost | US$0.000757 | US$0.001428 |
| Layer 2: expected fallback, `(1 - P) x US$7.60` | US$6.097674 | US$4.860465 |
| Layers 1 + 2 | US$6.098431 | US$4.861893 |
| Monthly cost at 8,000 claims, before fixed layer 3 | US$48,787.45 | US$38,895.15 |

The four measured levers explain the result. Success rate dominates expected cost because a US$7.60 human fallback is much larger than a fraction-of-a-cent inference call. Turn count is the next largest runtime lever; descriptor and observation sizes matter because they are sent repeatedly.

| Lever | Measured evidence | Cost implication |
|---|---|---|
| Tool block size B | Returning a required-document field costs 315 tokens; adding an eighth tool would cost 59,100 descriptor tokens over the measured pass | Avoid a permanently repeated descriptor |
| Turn count T | Grouped scheduling reduces 218 turns to 116 with identical outcomes | Reduces repeated context and latency |
| Observation size D | V2 coverage response adds 519 tokens across 67 calls | Small necessary field cost is explicit and bounded |
| Success rate P | V1 19.8%; V2 36.0% | Determines expected human fallback |

The V2 monthly estimate is US$44,975.15 at a pass rate ten percentage points below the observed value and US$32,815.15 ten points above it, plus the same unknown fixed platform layer. The conclusion survives this range: V2 remains cheaper than V1 under the stated fallback assumption.

For the break-even calculation, treat V1 as the cheaper configuration with C = US$0.000757 per run, V2 as the more expensive configuration with E = US$4.861893 including its measured failures, and F = US$7.60 per failure. The required cheap-configuration success rate is `1 - (E - C) / F = 36.04%`. V1's observed 19.8% falls well short, so V2 is the lower expected-cost choice in this scenario. This conclusion is conditional: strict human review did not establish that V2 reduces explanation-review workload, so code-check failure is only a provisional fallback proxy.

Evidence: `docs/report_section6.md`, `docs/D2a_tool_design.md`, `docs/evidence/measure_return_sizes.py`, and the matched live ledgers above.

## 5. Two reproduced failures

The first reproduced failure removes action de-duplication. On an expired pre-authorisation case, the agent revisits the same action instead of making progress. The final disposition remains correct, but the run expands from four to six turns and consumes substantially more tokens without triggering the ordinary caps. Final-action accuracy is therefore insufficient: a system can be right yet unnecessarily expensive and unstable.

The second failure removes the computed remaining policy limit. For CLM-9302, the annual limit looks sufficient when viewed alone, but earlier approved claims have already consumed most of it. Without the computed remainder, the agent approves a claim that should be escalated. This is a tool-interface defect, not simply a poor prompt: the necessary fact was not made available in the form required for a correct decision.

Evidence: `docs/report_section5.md` and the reproduced-failure scripts referenced there.

## 6. What we would not deploy

We would not deploy a multi-agent orchestrator-and-workers design for this version. A second reviewer agent could plausibly flag incomplete decision explanations - an important concern given the strict review results - but it would add another model call, a long shared transcript, hand-off ambiguity, and another source of structured-output failure. It would still need the same deterministic ledger checks before any write, so it does not remove the governing safety problem. Independent evidence calls already run in parallel inside one agent; adding multiple agents is not the same optimisation.

We therefore retain one ReAct control loop, deterministic validation, and a human confirmation gate. A future reviewer agent is worth testing only after the current evidence-completeness and parser failures are fixed, with a measured comparison against the single-agent baseline. We also would not deploy fully autonomous letter issuing, use cross-vendor pass rates as a simple model ranking, or interpret automated code checks as proof of explanation quality. These are limits of the current evidence, not claims of production readiness.
