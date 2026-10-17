---
kind: decision-record
id: ADR-008
title: "ADR-008 Memory is the default projection; graph and document backends are optional"
version: 1.0.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
y_statement: "In the context of where the projection is served from, facing the choice between a required graph database, memory only, and memory with optional backends behind one port, we decided for memory by default with Neo4j or Apache AGE as graph backends and MongoDB as the document projection, each filled by the sweep and bound only while the lake's pointer names the served build, and against a required database, to achieve zero idle cost for small deployments and a configuration switch for large ones, accepting three loaders and contract tests against emulators."
decision_drivers: ["Idle cost", "Scale when needed", "Safe switching"]
considered_options:
  - "A required graph database"
  - "Memory only"
  - "Memory with optional backends"
decision_outcome: "Memory with optional backends"
consequences:
  positive:
    - "Rollback is pointing back"
    - "Traversal is one code path over two primitives"
  negative:
    - "Three emulators in CI"
change_type: introduce
affects_artefacts: [BC-004, ABB-011]
resolves: [CN-005]
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ADR-008 Memory is the default projection; graph and document backends are optional

Status: active, as implemented at 0.3.0. This record is reversed from the implementation and the design notes; the decision was made in the code and the notes before it was written here.

## Context

A collection of tens of thousands of entities fits one process; larger ones do not, and every backend has a monthly floor.

## Decision

In the context of where the projection is served from, facing the choice between a required graph database, memory only, and memory with optional backends behind one port, we decided for memory by default with Neo4j or Apache AGE as graph backends and MongoDB as the document projection, each filled by the sweep and bound only while the lake's pointer names the served build, and against a required database, to achieve zero idle cost for small deployments and a configuration switch for large ones, accepting three loaders and contract tests against emulators.

## Options considered

- A required graph database
- Memory only
- Memory with optional backends

## Consequences

Positive: Rollback is pointing back; Traversal is one code path over two primitives.

Negative: Three emulators in CI.

## Affects

BC-004, ABB-011. Resolves CN-005.
