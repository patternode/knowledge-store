---
kind: abb
id: ABB-013
title: "ABB-013 Passage index"
short_name: "PIDX"
description: "Search of passages by meaning as its own store: one vector per passage, synced from the lake, so that a hit is a passage id the checks can re-read."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Knowledge graph"
part_of: BC-004
realises_capabilities: [CAP-006]
realised_by: [SBB-004]
requires:
  - { abb: ABB-002, cardinality: "1", rationale: "Fed from the kb/passages prefix" }
domains: [data]
interfaces:
  - { id: "I1", direction: "in", type: "event", description: "An ingestion job over kb/passages after the pipeline syncs a collection" }
  - { id: "I2", direction: "out", type: "query", description: "Retrieve: the nearest passages by meaning, each a passage id with collection scope" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "infra/modules/knowledge-base", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-013 Passage index

| Property | Value |
|---|---|
| ABB ID | ABB-013 |
| ABB Name | Passage index |
| Short Name | PIDX |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0, recalibrated to container grain |
| Category | Knowledge graph |
| Bounded context | BC-004 |
| Realises | CAP-006 |
| Realised by | SBB-004 |
| Grain | One C4 container: passes the container test of the [calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md) |

Search of passages by meaning as its own store: one vector per passage, synced from the lake, so that a hit is a passage id the checks can re-read.

## 1  Purpose

A graph answers in the terms someone defined; a question outside those terms still needs to find the passage that answers it. The index is a store with its own lifecycle, fed from the record and rebuilt from it when the embedding model changes (ADR-007, CN-004).

## 2  Building block

### 2.1  Component Diagram

The components below are the boxes of this container's component diagram, which is not yet drawn. The outside view of this block is its box in [AP-001](../../patterns/AP-001-ontology-driven-graphrag/index.md) and the row of its SBB in [RA-001](../../patterns/RA-001-knowledge-store-on-aws/index.md).

### 2.2  Components

- **Data source.** The lake's kb/passages prefix with a metadata sidecar per passage, synced per passage hash by the pipeline
- **Vectors.** One vector per passage, 1,024 dimensions, cosine, with collection, passage id, document, title and source as metadata
- **Retrieve.** Nearest passages for a query, filtered by collection and scope, through the passage tools (ABB-025)

### 2.3  Attributes

- **The passage as the unit.** A hit is a passage id, never a chunk the index invented
- **Rebuildability.** Dropped and re-embedded from silver
- **Cost.** Cents a month at rest

### 2.4  Semantic

Inside: the vectors and their metadata. Outside: the sync that writes the prefix (ABB-024) and the tools that query it (ABB-025).

### 2.5  Identity & Access Management

The Knowledge Base role reads kb/ in the lake; the passage tools role calls Retrieve; nothing else reaches it.

### 2.6  Observability

Ingestion job status per sync; the sweep's status records the last sync.

### 2.7  Governance & Policy Enforcement

Off switch: knowledge_base.enabled false removes it and the passage tools fall back to keyword search. The embedding model is a deployment input.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | event | An ingestion job over kb/passages after the pipeline syncs a collection |
| I2 | out | query | Retrieve: the nearest passages by meaning, each a passage id with collection scope |

### 3.4  Capability dependencies (requires)

- ABB-002 (1): Fed from the kb/passages prefix

## 4  Mapping

| Where | What |
|---|---|
| Code | `infra/modules/knowledge-base; src/knowledge_store/knowledge_graph/adapters/loading.py (sync)` |
| Capabilities | CAP-006 |
| Context | BC-004 |

## 5  Solution Building Block guidance

Realised by a Bedrock Knowledge Base over S3 Vectors (SBB-004). Under the local profile the passage tools search by keyword instead.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain |
