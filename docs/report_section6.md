# Report · Section 6 · Cost to serve

**Owner:** Liu Zeyuan  
**Evidence:** `docs/evidence/live_results_liu_v1.json` and PR #6,
`Preethi_gpt-4o-mini_v2_40cases_combined_results.json`.

---

## Draft

### 6 · Cost to serve

We separate cost into three layers. **Model cost** is the metered input and output tokens.
**Tool and platform cost** is zero in this prototype because the tools read local JSON, but
a production ledger must add database, network, storage and observability charges.
**Exception cost** is human review for escalations, guardrail stops and failed code checks;
this is likely to dominate the fractions of a cent spent on inference.

The matched experiment holds the model (`openai/gpt-4o-mini`), 40-case set, 86 trials,
guardrails and autonomy level constant, changing only the tool-descriptor prompt from v1
to v2. At the configured prices of US$0.15/M input tokens and US$0.60/M output tokens, v2
used 2.07× the input tokens and cost 88.7% more, but raised the automated code-check pass
rate by 16.3 percentage points. Median turns stayed at three. The v2 premium therefore
buys materially better task performance rather than fewer turns.

| Matched live ledger | v1 | v2 |
|---|---:|---:|
| Cases / trials | 40 / 86 | 40 / 86 |
| Code-check passes | 17 / 86 (19.8%) | 31 / 86 (36.0%) |
| Input tokens | 359,061 | 743,853 |
| Output tokens | 18,728 | 18,759 |
| Median turns | 3 | 3 |
| Total model cost | US$0.065094 | US$0.122829 |
| Model cost per trial | US$0.000757 | US$0.001428 |
| Model cost per code-check pass | US$0.003829 | US$0.003962 |
| Same-mix cost per 1,000 trials | US$0.757 | US$1.428 |
| Human judgement reasons passed | 1 / 40 | Pending in PR #6 |

For sensitivity, let **H** be the human cost of reviewing one failed automated trial. With
failure rate as the provisional review proxy, expected cost per trial is
`model cost + failure rate × H`. V2 reduces failures by 14/86 while adding US$0.000671
of model cost per trial, so it breaks even when **H > US$0.00412** per avoided review.
Any realistic human-review cost exceeds that threshold; under this assumption v2 is the
lower total-cost design despite its larger prompt.

Liu Zeyuan manually reviewed all 40 v1 judgement items: only 1 reason contained every
required evidential detail, while 39 omitted at least one required fact. The matched v2
judgement queue in PR #6 is still pending. The break-even calculation therefore uses the
automated code check as a provisional review proxy; the final report should recompute the
human-cost term once the v2 reasons have also been adjudicated.

---

## Recalculation formula

For either prompt version:

`total cost = fixed platform cost + trials × model cost per trial + reviewed trials × H`

The table reports measured model cost. Platform cost and **H** must be stated as explicit
deployment assumptions rather than hidden inside the API charge.
