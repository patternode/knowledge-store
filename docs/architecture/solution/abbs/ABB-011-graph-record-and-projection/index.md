---
kind: abb
id: ABB-011
title: "ABB-011 Graph record and projection"
short_name: "GRAPH"
description: "Gold as the record and every query store as a projection rebuilt from it: the index JSON for one process, named graphs in a SPARQL store, an optional graph database, an optional document store, each loaded by the sweep and served only while a pointer names the build."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Knowledge graph"
part_of: BC-004
realises_capabilities: [CAP-005]
realised_by: [SBB-003, SBB-011, SBB-014]
requires:
  - { abb: ABB-002, cardinality: "1", rationale: "Gold and the pointers" }
  - { abb: ABB-006, cardinality: "1", rationale: "The renditions for each store and the T-Box" }
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

# ABB-011 Graph record and projection

| Property | Value |
|---|---|
| ABB ID | ABB-011 |
| ABB Name | Graph record and projection |
| Short Name | GRAPH |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Knowledge graph |
| Bounded context | BC-004 |
| Realises | CAP-005 |
| Realised by | SBB-003, SBB-011, SBB-014 |

Gold as the record and every query store as a projection rebuilt from it: the index JSON for one process, named graphs in a SPARQL store, an optional graph database, an optional document store, each loaded by the sweep and served only while a pointer names the build.

## 1  Purpose

The record and the fast stores are different things. Projections can be dropped and rebuilt; a half-finished load is never served; a backend is a choice made at deployment, not in the model.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Projection.** Summary, ontology with counts, entities, passages, documents as JSON per version
- **SPARQL load.** DROP and INSERT per named graph, skipping unchanged hashes, dropping graphs off the chain, counting triples
- **Graph backend load.** Nodes with class labels and ancestors, edges with passages and scope; counts checked before the pointer moves; the previous build kept
- **Document load.** Entities, passages, documents into MongoDB with multikey indexes
- **Pointers.** graph.json, documents.json, sparql.json, kb.json

### 2.3  Attributes

- **Rebuildability.** Everything here is derived
- **Safe switching.** The pointer moves after the counts check; rollback is pointing back
- **Choice.** Memory by default; backends when a collection outgrows it

### 2.4  Semantic

Inside: projection and loading. Outside: querying (ABB-012), passage vectors (ABB-013).

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

- ABB-002 (1): Gold and the pointers
- ABB-006 (1): The renditions for each store and the T-Box

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/pipeline/project.py, load.py; graph/__init__.py, neo4j.py, age.py; portal_api/docstore.py (load)` |
| Capabilities | CAP-005 |
| Context | BC-004 |

## 5  Solution Building Block guidance

Realised by Neptune (SBB-003), the optional backends (SBB-011) and the index in the pipeline image (SBB-014).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
