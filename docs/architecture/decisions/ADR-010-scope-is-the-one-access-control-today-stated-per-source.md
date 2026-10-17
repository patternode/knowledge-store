---
kind: decision-record
id: ADR-010
title: "ADR-010 Scope is the one access control today, stated per source"
version: 1.0.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
y_statement: "In the context of what access control a document carries, facing the choice between one scope flag per source, per-document entitlements from the source, and a policy engine, we decided for scope (public or private) stated on the source and carried on every document, passage, entity, cell and link, enforced at every hop by one rule, and against entitlements for now, to achieve a control that is simple enough to be applied everywhere without a gap, accepting that classification and per-document entitlements are a designed extension (source-controls.md) not yet built."
decision_drivers: ["No gap in enforcement", "Simplicity"]
considered_options:
  - "One scope flag"
  - "Per-document entitlements"
  - "A policy engine at the tools"
decision_outcome: "One scope flag, with entitlements designed"
consequences:
  positive:
    - "Applied in the index, SPARQL, backends, Knowledge Base, structured tools, links"
  negative:
    - "Two-valued; a private reader sees every private source"
change_type: introduce
affects_artefacts: [BC-006, ABB-020]
resolves: [CN-002]
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ADR-010 Scope is the one access control today, stated per source

Status: active, as implemented at 0.3.0. This record is reversed from the implementation and the design notes; the decision was made in the code and the notes before it was written here.

## Context

Documents carry permissions, classifications and handling rules of their own; the store has one boolean.

## Decision

In the context of what access control a document carries, facing the choice between one scope flag per source, per-document entitlements from the source, and a policy engine, we decided for scope (public or private) stated on the source and carried on every document, passage, entity, cell and link, enforced at every hop by one rule, and against entitlements for now, to achieve a control that is simple enough to be applied everywhere without a gap, accepting that classification and per-document entitlements are a designed extension (source-controls.md) not yet built.

## Options considered

- One scope flag
- Per-document entitlements
- A policy engine at the tools

## Consequences

Positive: Applied in the index, SPARQL, backends, Knowledge Base, structured tools, links.

Negative: Two-valued; a private reader sees every private source.

## Affects

BC-006, ABB-020. Resolves CN-002.
