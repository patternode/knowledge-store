---
kind: decision-record
id: ADR-014
title: "ADR-014 The source adapter entry point group keeps its published name"
version: 1.0.0
status: active
created: 2026-11-24
last_modified: 2026-11-24
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
y_statement: "In the context of source adapters that other packages register under the entry point group knowledge_store.adapters, facing the engineering standard's rule that published names follow the contexts, we decided to keep the group's name as it is, to achieve a stable plug-in interface for adopters, accepting a name that no longer matches the Ingestion context's module path."
decision_drivers: ["Adopters' packages register source adapters under the group's name", "A renamed group would silently drop every adapter registered under the old one", "The engineering standard asks for a decision record for every exception"]
considered_options:
  - "Keep knowledge_store.adapters"
  - "Rename it to knowledge_store.ingestion.adapters, with a deprecation period reading both"
decision_outcome: "Keep knowledge_store.adapters"
consequences:
  positive:
    - "No adopter's adapter stops loading"
  negative:
    - "The group's name reads like a module path that no longer exists"
change_type: introduce
affects_artefacts: [BC-001]
resolves: []
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ADR-014 The source adapter entry point group keeps its published name

Status: active, made on 24 November 2026. It records an exception the engineering standard's appendix already lists, since section 8.3 asks for a decision record for each exception.

## Context

Source adapters are found through the Python entry point group `knowledge_store.adapters`, so a package outside this repository can add a source by registering under that group. When the code was cut by bounded context (ADR-011), adapters moved into the Ingestion context, and the group's name stopped matching any module path. The engineering standard lists the name as an exception but no decision record named it.

## Decision

In the context of source adapters that other packages register under the entry point group `knowledge_store.adapters`, facing the engineering standard's rule that published names follow the contexts, we decided to keep the group's name as it is, to achieve a stable plug-in interface for adopters, accepting a name that no longer matches the Ingestion context's module path. The group is a published name, part of Ingestion's contract, not a module path.

## Options considered

- Keep `knowledge_store.adapters`
- Rename it to `knowledge_store.ingestion.adapters`, reading both names for a deprecation period

## Consequences

Positive: no adopter's adapter stops loading. Negative: the group's name reads like a module path that no longer exists; the engineering standard's appendix says why.
