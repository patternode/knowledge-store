---
kind: abb
id: ABB-011
title: "ABB-011 Knowledge graph store"
short_name: "GRAPH"
description: "The graph projection of gold as a store the tools query: named graphs in a SPARQL store, one per document per version plus the T-Box, served only while a pointer names the build, with an optional graph or document backend behind the same port. Loaded by the sweep and written by nothing else."
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
  - { abb: ABB-002, cardinality: "1", rationale: "Gold is what it is built from; the pointers say which build is served" }
domains: [data, technology]
interfaces:
  - { id: "I1", direction: "in", type: "query", description: "Gold N-Quads along the chain; structured graphs; the index" }
  - { id: "I2", direction: "out", type: "query", description: "gold/<v>/index JSON; named graphs in the SPARQL store; a graph in Neo4j or AGE; documents in MongoDB; each with its pointer" }
  - { id: "I3", direction: "bidirectional", type: "request", description: "GraphStore: key_for, load, drop, keys, bind; Adjacency: node, adjacent" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/pipeline/project.py, load.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-011 Knowledge graph store

| Property | Value |
|---|---|
| ABB ID | ABB-011 |
| ABB Name | Knowledge graph store |
| Short Name | GRAPH |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Knowledge graph |
| Bounded context | BC-004 |
| Realises | CAP-005 |
| Realised by | SBB-003, SBB-011 |

The graph projection of gold as a store the tools query: named graphs in a SPARQL store, one per document per version plus the T-Box, served only while a pointer names the build, with an optional graph or document backend behind the same port. Loaded by the sweep and written by nothing else.

## 1  Purpose

The record and the fast stores are different things. Projections can be dropped and rebuilt; a half-finished load is never served; a backend is a choice made at deployment, not in the model.

## 2  Building block

### 2.1  Component Diagram

The components below are what runs inside this one container, listed per the building block calibration standard: none of them is a building block of its own. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Named graphs.** One per document per version plus the T-Box; per-graph hashes so an unchanged graph is not reloaded; graphs off the chain dropped
- **Query surface.** SPARQL over the fixed queries the tools build from the ontology; the two traversal primitives a graph backend offers
- **Pointers.** graph.json, documents.json and sparql.json name the build served; a build is kept until the next one checks
- **Graph backend.** Optional: nodes with class labels and ancestors, edges with passages and scope, a graph per load keyed by collection, version and build
- **Document projection.** Optional: entities, passages and documents in a document store with multikey indexes, so the API holds nothing in memory

### 2.3  Attributes

- **Rebuildability.** Everything here is derived
- **Safe switching.** The pointer moves after the counts check; rollback is pointing back
- **Choice.** Memory by default; backends when a collection outgrows it

### 2.4  Semantic

Inside: the stores and what they hold. Outside: building them (the projection and loading components of ABB-004) and querying them (ABB-012).

### 2.5  Identity & Access Management

The pipeline task alone writes Neptune and the backends.

### 2.6  Observability

Pointers with counts and build times; load errors recorded per step in the status.

### 2.7  Governance & Policy Enforcement

Memory is the default because every backend has a monthly floor (ADR-008).

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | data | Gold N-Quads along the chain; structured graphs; the index |
| I2 | out | projection | gold/<v>/index JSON; named graphs in the SPARQL store; a graph in Neo4j or AGE; documents in MongoDB; each with its pointer |
| I3 | port | port | GraphStore: key_for, load, drop, keys, bind; Adjacency: node, adjacent |

### 3.4  Capability dependencies (requires)

- ABB-002 (1): Gold is what it is built from; the pointers say which build is served

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/graph/__init__.py, sparql.py, neo4j.py, age.py; portal_api/docstore.py; infra/modules/knowledge-graph` |
| Capabilities | CAP-005 |
| Context | BC-004 |

## 5  Solution Building Block guidance

Realised by Neptune (SBB-003) and the optional backends (SBB-011). With the graph store off, the tools answer from the index in the lake in one process; that is a mode of ABB-012, not a store.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.2.0 | 2026-10-17 | Recalibrated to container grain: the projection and loading stages moved to ABB-004; the block is the store; renamed from Graph record and projection |
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
