---
kind: abb
id: ABB-013
title: "ABB-013 Passage index"
short_name: "PSRCH"
description: "One vector per passage, so a hit is a passage id: a store synced from silver by the sweep and queried by meaning, with the collection and scope filters, by the passage tools."
version: 0.2.0
status: draft
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Knowledge graph"
part_of: BC-004
realises_capabilities: [CAP-006]
realised_by: [SBB-004]
requires:
  - { abb: ABB-002, cardinality: "1", rationale: "The kb prefix it ingests, the pointer, and silver for the text" }
domains: [application, data]
interfaces:
  - { id: "I1", direction: "out", type: "query", description: "kb/passages/<collection>/<id>.txt with metadata; an ingestion job" }
  - { id: "I2", direction: "in", type: "request", description: "search_passages (query, collection, scope); read_passages (ids) (CT-003)" }
  - { id: "I3", direction: "out", type: "query", description: "Passages with ids, documents and titles; method vector or keyword" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/pipeline/load.py (sync)", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-013 Passage index

| Property | Value |
|---|---|
| ABB ID | ABB-013 |
| ABB Name | Passage index |
| Short Name | PSRCH |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Knowledge graph |
| Bounded context | BC-004 |
| Realises | CAP-006 |
| Realised by | SBB-004 |

One vector per passage, so a hit is a passage id: a store synced from silver by the sweep and queried by meaning, with the collection and scope filters, by the passage tools.

## 1  Purpose

Questions that describe a situation share no words with the article that answers them. Meaning search finds it, and because the unit is the passage, the hit meets the graph at the same id.

## 2  Building block

### 2.1  Component Diagram

The components below are what runs inside this one container, listed per the building block calibration standard: none of them is a building block of its own. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Index.** One vector per passage, 1,024 dimensions, cosine; chunking off so the passage is the unit
- **Data source.** The lake's kb/passages prefix with metadata sidecars; an ingestion job per change
- **Filters.** collection, scope, passage id, document, title and source in the metadata

### 2.3  Attributes

- **Cost.** Cents at rest; embedding once per passage
- **Scope.** The filter and the re-check

### 2.4  Semantic

Inside: the index and what it holds. Outside: writing it (the passage sync component of ABB-004), querying it and falling back when it is off (ABB-012).

### 2.5  Identity & Access Management

The Knowledge Base role reads kb/ only and the embedding model only; the passage tools Lambda may Retrieve.

### 2.6  Observability

kb.json records what was synced; ingestion job state.

### 2.7  Governance & Policy Enforcement

knowledge_base.enabled; one embedding model per deployment.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | out | data | kb/passages/<collection>/<id>.txt with metadata; an ingestion job |
| I2 | in | request | search_passages (query, collection, scope); read_passages (ids) (CT-003) |
| I3 | out | result | Passages with ids, documents and titles; method vector or keyword |

### 3.4  Capability dependencies (requires)

- ABB-002 (1): The kb prefix it ingests, the pointer, and silver for the text

## 4  Mapping

| Where | What |
|---|---|
| Code | `infra/modules/knowledge-base; src/knowledge_store/pipeline/load.py (sync); tools/passages.py (Retrieve)` |
| Capabilities | CAP-006 |
| Context | BC-004 |

## 5  Solution Building Block guidance

Realised by Bedrock Knowledge Base on S3 Vectors (SBB-004). With it off, the passage tools fall back to keywords over the index in the lake.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.2.0 | 2026-10-17 | Recalibrated to container grain: the sync moved to ABB-004 and the retrieval tools to ABB-012; the block is the store; renamed from Passage search by meaning |
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
