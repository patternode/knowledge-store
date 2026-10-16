---
kind: decision-record
id: ADR-002
title: "ADR-002 Nothing is shown unchecked: claims with citations, verified by code"
version: 1.0.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
y_statement: "In the context of what reaches a reader, facing the choice between showing the model's answer with retrieved context and showing only what code verified, we decided for structured claims with citations (a passage and a verbatim quote, a cell and a value, or a figure and its computation), each re-read as the caller and checked, with a contextual-grounding guardrail and one repair round, and against showing prose, to achieve answers a reader can check sentence by sentence, accepting fewer and shorter answers and an abstention when nothing survives."
decision_drivers: ["Verifiability", "Scope safety (re-reading as the caller)", "Testability without a model"]
considered_options:
  - "Show the answer with its retrieved context"
  - "Show only verified claims"
  - "Show the answer and flag unverified sentences"
decision_outcome: "Show only verified claims"
consequences:
  positive:
    - "OC-001-M1 is 100 percent by construction"
    - "The checks run in the test suite with a fake model"
    - "A public caller cannot be shown a private passage"
  negative:
    - "The portal's fallback loop does not meet this rule (CN-006)"
    - "Abstentions where a looser system would answer"
change_type: introduce
affects_artefacts: [BC-005, ABB-015, ABB-014]
resolves: []
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ADR-002 Nothing is shown unchecked: claims with citations, verified by code

Status: active, as implemented at 0.3.0. This record is reversed from the implementation and the design notes; the decision was made in the code and the notes before it was written here.

## Context

A model's answer is prose it may have invented. The store exists to make answers checkable.

## Decision

In the context of what reaches a reader, facing the choice between showing the model's answer with retrieved context and showing only what code verified, we decided for structured claims with citations (a passage and a verbatim quote, a cell and a value, or a figure and its computation), each re-read as the caller and checked, with a contextual-grounding guardrail and one repair round, and against showing prose, to achieve answers a reader can check sentence by sentence, accepting fewer and shorter answers and an abstention when nothing survives.

## Options considered

- Show the answer with its retrieved context
- Show only verified claims
- Show the answer and flag unverified sentences

## Consequences

Positive: OC-001-M1 is 100 percent by construction; The checks run in the test suite with a fake model; A public caller cannot be shown a private passage.

Negative: The portal's fallback loop does not meet this rule (CN-006); Abstentions where a looser system would answer.

## Affects

BC-005, ABB-015, ABB-014.
