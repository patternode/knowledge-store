---
kind: abb
id: ABB-008
title: "ABB-008 Table mapping definition"
short_name: "MAP"
description: "Which table fills which class, with its key, columns, scope and location, and the metrics over it, checked against the ontology at publish and rendered for the sweep, the tools and a later virtual knowledge graph."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Ontology"
part_of: BC-002
realises_capabilities: [CAP-007]
realised_by: [SBB-014]
requires:
  - { abb: ABB-006, cardinality: "1", rationale: "A mapping is part of a version" }
domains: [data, business]
interfaces:
  - { id: "I1", direction: "in", type: "query", description: "mappings.yaml and metrics.osi.yaml beside the master (CT-008)" }
  - { id: "I2", direction: "out", type: "query", description: "structured/mapping.json and r2rml/mapping.ttl renditions" }
  - { id: "I3", direction: "out", type: "query", description: "The mapping's change kind, folded into the version's" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/structured/mapping.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-008 Table mapping definition

| Property | Value |
|---|---|
| ABB ID | ABB-008 |
| ABB Name | Table mapping definition |
| Short Name | MAP |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Ontology |
| Bounded context | BC-002 |
| Realises | CAP-007 |
| Realised by | SBB-014 |

Which table fills which class, with its key, columns, scope and location, and the metrics over it, checked against the ontology at publish and rendered for the sweep, the tools and a later virtual knowledge graph.

## 1  Purpose

A table stays a table only if the store knows its schema in the ontology's terms. The mapping is that knowledge, and making it part of the version means a column becomes an attribute only when a person publishes it.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Mapping model.** tables, logical table, location, class, key, scope, columns as attribute or relation with datatype, range, match
- **Checks.** Class exists, attribute domain fits, datatype agrees, range is a class, match is present, names unique; metric SELECT is read-only and names a logical table
- **Renditions.** JSON for the sweep and tools; R2RML for Ontop later

### 2.3  Attributes

- **Consistency.** Refused at publish, never discovered at bind
- **Portability.** The R2RML is the same triples maps a virtual graph would use

### 2.4  Semantic

Inside: the definition and its checks. Outside: binding the file (ABB-010) and querying it (ABB-012).

### 2.5  Identity & Access Management

Curators; column names are untrusted until published.

### 2.6  Observability

Publish reports the first failing term.

### 2.7  Governance & Policy Enforcement

A mapping change is classified like an ontology change and bumps the version accordingly.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | artefact | mappings.yaml and metrics.osi.yaml beside the master (CT-008) |
| I2 | out | artefact | structured/mapping.json and r2rml/mapping.ttl renditions |
| I3 | out | classification | The mapping's change kind, folded into the version's |

### 3.4  Capability dependencies (requires)

- ABB-006 (1): A mapping is part of a version

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/structured/mapping.py` |
| Capabilities | CAP-007 |
| Context | BC-002 |

## 5  Solution Building Block guidance

Realised in the pipeline image and the CLI; the live-source case (CN-003) keeps this definition and changes only the location.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
