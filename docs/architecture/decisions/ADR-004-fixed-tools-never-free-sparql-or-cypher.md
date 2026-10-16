---
kind: decision-record
id: ADR-004
title: "ADR-004 Fixed tools, never free SPARQL or Cypher"
version: 1.0.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
y_statement: "In the context of how the agent reaches the stores, facing the choice between free-form queries and a fixed set of read-only tools, we decided for twelve fixed tools defined in the ontology's terms, with no SPARQL or Cypher tool, and against free queries, to achieve scope enforcement at a shared endpoint and read-only access by construction, accepting that a question the tools cannot express is answered by the model from what it can fetch, or not at all."
decision_drivers: ["Scope enforcement", "Read-only by construction", "Explainable answers (every step is a tool call)"]
considered_options:
  - "Free SPARQL with a read-only role"
  - "Fixed tools"
  - "Templates with model-filled slots"
decision_outcome: "Fixed tools"
consequences:
  positive:
    - "One implementation, three surfaces"
    - "Every argument clamped"
  negative:
    - "Some questions need a tool that does not exist yet"
change_type: introduce
affects_artefacts: [BC-004, ABB-012]
resolves: []
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ADR-004 Fixed tools, never free SPARQL or Cypher

Status: active, as implemented at 0.3.0. This record is reversed from the implementation and the design notes; the decision was made in the code and the notes before it was written here.

## Context

A model could be given a query language; many graph question-answering systems do that.

## Decision

In the context of how the agent reaches the stores, facing the choice between free-form queries and a fixed set of read-only tools, we decided for twelve fixed tools defined in the ontology's terms, with no SPARQL or Cypher tool, and against free queries, to achieve scope enforcement at a shared endpoint and read-only access by construction, accepting that a question the tools cannot express is answered by the model from what it can fetch, or not at all.

## Options considered

- Free SPARQL with a read-only role
- Fixed tools
- Templates with model-filled slots

## Consequences

Positive: One implementation, three surfaces; Every argument clamped.

Negative: Some questions need a tool that does not exist yet.

## Affects

BC-004, ABB-012.
