# Report · Section 3 · Multi-model comparison

**Owner:** Iris

## Draft

### 3 · Cross-model results

Every live result uses the frozen 40-case Problem A set, v2 descriptors, and 86 trials
(ordinary cases once; negative cases three times), except Liu's matched v1 control. The
headline is the automated code check. It must not be read as a pure intelligence ranking:
the runner falls back to `escalate` when a provider does not return parseable JSON, so a
format-compliance failure becomes a code-check failure. We retain those outcomes rather than
changing parser or prompt midway through the comparison.

| Model / prompt | Code-check pass | Median turns | Total cost | Interpretation |
|---|---:|---:|---:|---|
| `openai/gpt-4o-mini` v2 | 31/86 (36.0%) | 3 | US$0.122829 | Matched v2 arm; source PR #6 |
| `qwen/qwen3.8-flash` v2 | 19/86 (22.1%) | 2 | US$0.153983 | Full retained battery |
| `google/gemini-3.8-flash` v2 | 8/86 (9.3%) | 2 | US$1.037978 | 68/86 JSON parse fallbacks; 8/18 among completed trials |
| `mistralai/mistral-small-3.2-24b-instruct` v2 | 6/86 (7.0%) | 2 | US$0.042586 | Retained tool/harness stops; not a clean capability score |
| `anthropic/claude-haiku-4.5` v2 | 0/86 (0%) | 1 | US$0.655554 | 86/86 JSON parse fallbacks; no trial reached an adjudication |
| `openai/gpt-4o-mini` v1 | 17/86 (19.8%) | 3 | US$0.065094 | Control arm; compare only with the v2 row above |

Haiku's result is a compatibility finding, not a claim that the model reasoned incorrectly
on every case: each trial made a real paid call and acquired the claim, then the next model
message was unparseable under the shared JSON contract. Altering the live parser after other
batteries had run would invalidate the same-prompt comparison, so we report the 0/86 headline
and the 86/86 fallback rate together. The valid causal descriptor comparison remains the
matched `gpt-4o-mini` v1/v2 pair in Section 2; cross-provider rows are descriptive only.

**Evidence:** `docs/evidence/live_results_iris_claude_v2.json`,
`live_results.json`, `live_results_harry.json`, `live_results_kou_v2.json`, and
`live_results_liu_v1.json`.
