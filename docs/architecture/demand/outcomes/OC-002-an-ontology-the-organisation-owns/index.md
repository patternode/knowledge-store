---
kind: outcome
id: OC-002
title: "OC-002 An ontology the organisation owns"
description: "The ontology that types the graph is curated by people, released in versions whose class bounds the cost of the change, and grown from what extraction found it lacked."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
kpi: "Ontology versions published by a person, and re-extraction bounded by the version's class"
kpi_target: { value: "every version curated; a patch re-extracts nothing, a minor only its delta, a major everything", unit: "rule", measurement: "the publish command refuses an understated bump; the sweep applies the class" }
business_rationale: "A graph typed by whatever a model proposed drifts with every run. A graph typed by an ontology a person published, versioned and classified, is something an organisation can govern, and the terms the model finds missing become proposals rather than silent additions."
time_horizon: medium
measures:
  - { id: OC-002-M1, measure: "Published versions whose terms a person curated (curated mode), as a share of versions", target: 100, unit: "percent" }
  - { id: OC-002-M2, measure: "Documents re-extracted after a minor version, as a share of the collection", target: "the delta only", unit: "share" }
  - { id: OC-002-M3, measure: "Candidate terms carried into a proposed next version rather than lost", target: "all with two or more documents or a request", unit: "rule" }
owned_by_platform: PL-001
requires_capabilities: [CAP-003, CAP-004, CAP-012]
realised_by_use_cases: [UC-003, UC-004, UC-005]
provenance:
  origin: ai-generated
  review_state: ai-raw
supported_by_use_cases: [UC-003, UC-004, UC-005]
---

# OC-002 An ontology the organisation owns

| Property | Value |
|---|---|
| Outcome ID | OC-002 |
| Measure | Versions published by a person; re-extraction bounded by the version's class |
| Owned by | PL-001 Knowledge Store |

## Definition

A collection's ontology is a Turtle master a person edits, published as an immutable version whose number says what changed: descriptive (patch), additive (minor), semantic or removal (major). Each class decides what the next sweep does, from nothing to a full re-extraction. Terms extraction could not place, and requests kept from the workbench, become the proposal for the next version; nothing enters the ontology without a person publishing it, in curated mode.

## Business rationale

The ontology is the organisation's statement of what its documents are about. Owning it means a person can read it, change it, and know what a change costs before making it. The store makes that possible by separating the master from its renditions, classifying versions, and keeping candidates out of the graph until published.

## Traceability

Requires CAP-003 ontology lifecycle, CAP-004 extraction (delta and full, and the candidates it records) and CAP-012 the workbench's ontology requests. Realised by UC-003 bring an ontology, UC-004 discover and curate one, UC-005 grow it.
