---
kind: abb
id: ABB-011
title: "ABB-011 Knowledge graph"
short_name: "GRAPH"
description: "The graph projection of the gold record: one named graph per document per ontology version plus the T-Box, in a SPARQL store the graph tools query read-only, rebuilt from the lake whenever needed."
version: 0.2.0
status: draft
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Knowledge graph"
part_of: BC-004
realises_capabilities: [CAP-005]
realised_by: [SBB-003, SBB-011]
requires:
  - { abb: ABB-002, cardinality: "1", rationale: "Loaded from gold; rebuilt from it" }
domains: [data]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "DROP and INSERT per named graph, from the pipeline's load stage" }
  - { id: "I2", direction: "out", type: "query", description: "Read-only SPARQL over the named graphs, one per document per version, and the T-Box" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "infra/modules/knowledge-graph", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-011 Knowledge graph

| Property | Value |
|---|---|
| ABB ID | ABB-011 |
| ABB Name | Knowledge graph |
| Short Name | GRAPH |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0, recalibrated to container grain |
| Category | Knowledge graph |
| Bounded context | BC-004 |
| Realises | CAP-005 |
| Realised by | SBB-003, SBB-011 |
| Grain | One C4 container: passes the container test of the [calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md) |

The graph projection of the gold record: one named graph per document per ontology version plus the T-Box, in a SPARQL store the graph tools query read-only, rebuilt from the lake whenever needed.

## 1  Purpose

The record is RDF per document in the lake (ADR-001); a graph store is a projection that makes traversal and aggregation fast and keeps provenance by graph. It is a container because it holds its own data with its own lifecycle and can be replaced by another product (CN-001, SBB-011) without rebuilding its neighbours.

## 2  Building block

### 2.1  Component Diagram

The components below are the boxes of this container's component diagram, which is not yet drawn. The outside view of this block is its box in [PAT-001](../../patterns/PAT-001-ontology-driven-graphrag/index.md) and the row of its SBB in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Components

- **Named graphs.** One per document per version, loaded by DROP and INSERT with per-graph hashes so an unchanged document is not reloaded
- **T-Box.** The ontology version's classes, relations and attributes as one graph
- **Pointers.** gold/graph and the build id that say which load is current
- **Optional backends.** A labelled property graph or a document projection loaded beside it (SBB-011), each a graph per load keyed by collection, version and build

### 2.3  Attributes

- **Rebuildability.** Dropped and reloaded from gold at any time
- **Isolation.** Private subnets, IAM authentication, port open to two security groups only
- **Read-only to readers.** Only the pipeline writes

### 2.4  Semantic

Inside: the graphs and what they are keyed by. Outside: the queries, which are fixed and live in the graph tools (ABB-012), and the projection code, which runs in the pipeline (ABB-024).

### 2.5  Identity & Access Management

IAM database authentication; the pipeline task role writes, the graph tools role reads; nothing else reaches it.

### 2.6  Observability

Load counts and hashes in the sweep's status; the cluster's own metrics and a thirty-second query timeout.

### 2.7  Governance & Policy Enforcement

Off switch: knowledge_graph.enabled false removes it and the tools answer from the in-memory projection (ADR-008). Memory is the default projection; Neptune or a backend is the choice at scale (CN-001, CN-005).

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | request | DROP and INSERT per named graph, from the pipeline's load stage |
| I2 | out | query | Read-only SPARQL over the named graphs, one per document per version, and the T-Box |

### 3.4  Capability dependencies (requires)

- ABB-002 (1): Loaded from gold; rebuilt from it

## 4  Mapping

| Where | What |
|---|---|
| Code | `infra/modules/knowledge-graph; src/knowledge_store/graph/sparql.py (the loader side), neo4j.py, age.py` |
| Capabilities | CAP-005 |
| Context | BC-004 |

## 5  Solution Building Block guidance

Realised by Amazon Neptune (SBB-003) in the deployed profile; Neo4j, Apache AGE or MongoDB (SBB-011) as alternatives; the in-memory projection under the local profile.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain |
