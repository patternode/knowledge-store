---
kind: decision-record
id: ADR-005
title: "ADR-005 Ontology versions are immutable and classified, and the bump decides the cost"
version: 1.0.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
y_statement: "In the context of changing a collection's ontology, facing the choice between editing in place and publishing versions, we decided for immutable semver versions whose change kind (descriptive, additive, semantic, removal) is computed from the diff and whose bump is refused when understated, with additive versions chaining to a base and extracted as deltas, and against editing in place, to achieve a known cost per change and a governed ontology, accepting a chain to walk and a heuristic delta selection."
decision_drivers: ["Cost of a change known before it is made", "A person publishes", "Consumers read renditions, never the master"]
considered_options:
  - "Edit the master in place and re-extract everything"
  - "Versions with a computed class and a delta path"
  - "Versions with full re-extraction always"
decision_outcome: "Versions with a computed class and a delta path"
consequences:
  positive:
    - "A patch costs no model call"
    - "Renditions are reproducible"
  negative:
    - "Delta selection can miss a document (extract --all-delta exists)"
    - "The bind module carries a copy of the chain walk"
change_type: introduce
affects_artefacts: [BC-002, ABB-006, ABB-004]
resolves: []
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ADR-005 Ontology versions are immutable and classified, and the bump decides the cost

Status: active, as implemented at 0.3.0. This record is reversed from the implementation and the design notes; the decision was made in the code and the notes before it was written here.

## Context

Ontologies that change freely make re-extraction unbounded or silent.

## Decision

In the context of changing a collection's ontology, facing the choice between editing in place and publishing versions, we decided for immutable semver versions whose change kind (descriptive, additive, semantic, removal) is computed from the diff and whose bump is refused when understated, with additive versions chaining to a base and extracted as deltas, and against editing in place, to achieve a known cost per change and a governed ontology, accepting a chain to walk and a heuristic delta selection.

## Options considered

- Edit the master in place and re-extract everything
- Versions with a computed class and a delta path
- Versions with full re-extraction always

## Consequences

Positive: A patch costs no model call; Renditions are reproducible.

Negative: Delta selection can miss a document (extract --all-delta exists); The bind module carries a copy of the chain walk.

## Affects

BC-002, ABB-006, ABB-004.
