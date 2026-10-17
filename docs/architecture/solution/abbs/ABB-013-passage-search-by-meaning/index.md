---
kind: abb
id: ABB-013
title: "ABB-013 Passage search by meaning"
short_name: "PSRCH"
description: "One vector per passage so a hit is a passage id, synced from silver, retrieved by meaning with the collection and scope filters, with a keyword fallback and a read by id that falls back to silver."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Knowledge graph"
part_of: BC-004
realises_capabilities: [CAP-006]
realised_by: [SBB-004, SBB-005]
requires:
  - { abb: ABB-003, cardinality: "1", rationale: "The passages" }
  - { abb: ABB-002, cardinality: "1", rationale: "The kb prefix and the pointer" }
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

# ABB-013 Passage search by meaning

| Property | Value |
|---|---|
| ABB ID | ABB-013 |
| ABB Name | Passage search by meaning |
| Short Name | PSRCH |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Knowledge graph |
| Bounded context | BC-004 |
| Realises | CAP-006 |
| Realised by | SBB-004, SBB-005 |

One vector per passage so a hit is a passage id, synced from silver, retrieved by meaning with the collection and scope filters, with a keyword fallback and a read by id that falls back to silver.

## 1  Purpose

Questions that describe a situation share no words with the article that answers them. Meaning search finds it, and because the unit is the passage, the hit meets the graph at the same id.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Sync.** Per-passage hash of text, scope and title; deletions; one ingestion job per change
- **Retrieve.** Filtered, then re-checked against metadata
- **Keyword fallback.** tf-idf over the index when the Knowledge Base is off
- **Read.** From the projection, then silver

### 2.3  Attributes

- **Cost.** Cents at rest; embedding once per passage
- **Scope.** The filter and the re-check

### 2.4  Semantic

Inside: the passage index and its tools. Outside: the graph.

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

- ABB-003 (1): The passages
- ABB-002 (1): The kb prefix and the pointer

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/pipeline/load.py (sync); tools/passages.py` |
| Capabilities | CAP-006 |
| Context | BC-004 |

## 5  Solution Building Block guidance

Realised by Bedrock Knowledge Base on S3 Vectors (SBB-004) and the passage tools Lambda (SBB-005).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
