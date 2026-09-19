# Report · Section 0 · Why an agent?

**Owner:** Liu Zeyuan  
**Draft budget:** about 210 words. This section does not depend on the live-battery results.

---

## Draft

### 0 · Why an agent?

Problem A is not a single-shot classification task. A claim can be triaged only after
joining facts held separately across the claim, member, policy, procedure coverage,
provider, pre-authorisation, document and duplicate-history records. The next useful
lookup depends on the previous result: a lapsed policy ends the investigation, a covered
procedure may require a pre-authorisation check, and a missing required document changes
the outcome to `request_document`. A fixed workflow would either query every source for
every claim or encode an expanding set of brittle branches. Giving all records to one
chatbot call would expose unnecessary data and would not demonstrate an agent loop.

We therefore use a bounded, tool-using agent. It begins with a claim identifier, retrieves
only the evidence needed for that case, and selects the next tool from the observations
returned so far. Independent lookups may be grouped, while dependent calls remain ordered.
The agent then produces one of three controlled outcomes: `approve_in_principle`,
`request_document`, or `escalate`.

This adaptability is deliberately constrained. A human confirmation gate protects the
irreversible decision-letter action; step and token ceilings bound the run; call
de-duplication prevents loops; and the evidence record logs tool calls, turns, tokens,
cost and guardrail events. The result is adaptive reasoning that remains auditable,
reproducible and measurable rather than unrestricted autonomy.

---

## Editor note

Keep this section independent of D6. Insert measured V1 costs and pass rates only after
the live battery is complete, so D0 remains the architectural justification and D6 carries
the quantitative cost argument.
