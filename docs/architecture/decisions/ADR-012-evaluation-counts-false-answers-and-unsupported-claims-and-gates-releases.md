---
kind: decision-record
id: ADR-012
title: "ADR-012 Evaluation counts false answers and unsupported claims, and gates releases on a baseline"
version: 1.0.0
status: active
created: 2026-10-20
last_modified: 2026-10-20
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
y_statement: "In the context of an evaluator whose false positives counted a cited hedge as a wrong answer and never counted a wrong claim on an answerable question, facing the choice between keeping the measure, adding a model judge to the score, and redefining the measures with a claim verifier kept apart from the judge, we decided for false answers judged by whether the agent declined, unsupported claims counted on every question by a claim verifier shared with Answering, figures matched at the answer's own rounding, and a baseline gate, with Inspect AI as an optional runner, and against a model judge in the score, to achieve measures that say what went wrong and stay deterministic, accepting that a local verifier must be calibrated on labelled claims before it gates."
decision_drivers: ["The score stays free of model judges (UC-007)", "False positives the evaluator itself caused", "A release gate other products can rely on"]
considered_options:
  - "Keep the abstention-flag measure"
  - "A model judge in the score"
  - "Redefined measures, a shared claim verifier, a baseline gate"
decision_outcome: "Redefined measures, a shared claim verifier, a baseline gate"
consequences:
  positive:
    - "A cited hedge is a right decline; an invented fact is a false answer"
    - "Unsupported claims are counted on answerable questions too"
    - "Applications bring truth sources and question sets, not harnesses"
  negative:
    - "The lexical verifier is a floor; meaning needs HHEM or the Guardrail"
    - "Inspect AI is pre-1.0 and pinned"
change_type: introduce
affects_artefacts: [BC-007, BC-005, SV-009, ABB-021]
resolves: []
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ADR-012 Evaluation counts false answers and unsupported claims, and gates releases on a baseline

Status: active. This is Knowledge Store's application of patternode-architecture ADR-048 (the evaluation framework), made on 20 October 2026.

## Context

The report's "false positives" were unanswerable questions where the agent's abstained flag was false. A reply that declined while citing a true passage counted as one, and a wrong claim on an answerable question was never counted at all. The citation check confirms that a quote appears in its passage, not that the passage supports the claim.

## Decision

In the context of an evaluator whose false positives counted a cited hedge as a wrong answer and never counted a wrong claim on an answerable question, facing the choice between keeping the measure, adding a model judge to the score, and redefining the measures with a claim verifier kept apart from the judge, we decided for false answers judged by whether the agent declined, unsupported claims counted on every question by a claim verifier shared with Answering, figures matched at the answer's own rounding, and a baseline gate, with Inspect AI as an optional runner, and against a model judge in the score, to achieve measures that say what went wrong and stay deterministic, accepting that a local verifier must be calibrated on labelled claims before it gates.

## Options considered

- Keep the abstention-flag measure
- A model judge in the score
- Redefined measures, a shared claim verifier, a baseline gate

## Consequences

Positive: A cited hedge is a right decline; an invented fact is a false answer. Unsupported claims are counted on answerable questions too. Applications bring truth sources and question sets, not harnesses.

Negative: The lexical verifier is a floor; meaning needs HHEM or the Guardrail. Inspect AI is pre-1.0 and pinned.

## Affects

BC-007, BC-005, SV-009, ABB-021.
