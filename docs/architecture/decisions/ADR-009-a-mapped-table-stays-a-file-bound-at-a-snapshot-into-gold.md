---
kind: decision-record
id: ADR-009
title: "ADR-009 A mapped table stays a file, bound at a snapshot into gold"
version: 1.0.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
y_statement: "In the context of structured sources, facing the choice between extracting tables as prose, loading them into a relational store, and binding the file at its content hash into gold as rows and cells, we decided for binding with the mapping published as part of the ontology version and cell and figure citations recomputed at check time, and against a relational store, to achieve table facts with the same provenance discipline as passage facts and no new store, accepting that a live source needs a virtual knowledge graph later."
decision_drivers: ["Citable cells", "No new store", "The mapping governed with the version"]
considered_options:
  - "Tables as prose"
  - "A relational store"
  - "Snapshots bound into gold"
decision_outcome: "Snapshots bound into gold"
consequences:
  positive:
    - "Old snapshots keep citations valid"
    - "The SQL of a metric is parsed, never run"
  negative:
    - "Live sources are a separate design (CN-003)"
change_type: introduce
affects_artefacts: [BC-003, ABB-008, ABB-010, ABB-012]
resolves: [CN-003]
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ADR-009 A mapped table stays a file, bound at a snapshot into gold

Status: active, as implemented at 0.3.0. This record is reversed from the implementation and the design notes; the decision was made in the code and the notes before it was written here.

## Context

A table parsed as prose cannot be totalled or cited by cell.

## Decision

In the context of structured sources, facing the choice between extracting tables as prose, loading them into a relational store, and binding the file at its content hash into gold as rows and cells, we decided for binding with the mapping published as part of the ontology version and cell and figure citations recomputed at check time, and against a relational store, to achieve table facts with the same provenance discipline as passage facts and no new store, accepting that a live source needs a virtual knowledge graph later.

## Options considered

- Tables as prose
- A relational store
- Snapshots bound into gold

## Consequences

Positive: Old snapshots keep citations valid; The SQL of a metric is parsed, never run.

Negative: Live sources are a separate design (CN-003).

## Affects

BC-003, ABB-008, ABB-010, ABB-012. Resolves CN-003.
