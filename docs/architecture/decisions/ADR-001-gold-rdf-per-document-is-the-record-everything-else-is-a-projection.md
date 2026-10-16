---
kind: decision-record
id: ADR-001
title: "ADR-001 Gold RDF per document is the record; everything else is a projection"
version: 1.0.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
y_statement: "In the context of where the facts live, facing the choice between a database as the source of truth and files per document, we decided for SHACL-valid N-Quads per document per ontology version in the lake as the record, with the index, Neptune, any graph database and the passage index as projections rebuilt from it, and against a database as the record, to achieve rebuildability, auditability per document and a store that idles at nothing, accepting that projections lag the record by a sweep and that a graph database is one more thing to rebuild."
decision_drivers: ["Rebuildability", "Audit per document and version", "Idle cost"]
considered_options:
  - "A graph database as the record"
  - "RDF files per document as the record"
  - "Both, kept in step by writes"
decision_outcome: "RDF files as the record"
consequences:
  positive:
    - "Any projection can be dropped and rebuilt"
    - "A failed load is never served: the pointer moves after the counts check"
    - "A version's gold is immutable and checksummed"
  negative:
    - "A projection lags by one sweep"
    - "Three loaders to keep correct"
change_type: introduce
affects_artefacts: [BC-003, BC-004, ABB-011, ABB-002]
resolves: []
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ADR-001 Gold RDF per document is the record; everything else is a projection

Status: active, as implemented at 0.3.0. This record is reversed from the implementation and the design notes; the decision was made in the code and the notes before it was written here.

## Context

The lake borrows the medallion names, and a reader could take gold for a quality tier and the index or the graph database for the truth.

## Decision

In the context of where the facts live, facing the choice between a database as the source of truth and files per document, we decided for SHACL-valid N-Quads per document per ontology version in the lake as the record, with the index, Neptune, any graph database and the passage index as projections rebuilt from it, and against a database as the record, to achieve rebuildability, auditability per document and a store that idles at nothing, accepting that projections lag the record by a sweep and that a graph database is one more thing to rebuild.

## Options considered

- A graph database as the record
- RDF files per document as the record
- Both, kept in step by writes

## Consequences

Positive: Any projection can be dropped and rebuilt; A failed load is never served: the pointer moves after the counts check; A version's gold is immutable and checksummed.

Negative: A projection lags by one sweep; Three loaders to keep correct.

## Affects

BC-003, BC-004, ABB-011, ABB-002.
