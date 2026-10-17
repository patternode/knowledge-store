---
kind: abb
id: ABB-025
title: "ABB-025 Passage tools"
short_name: "PTOOLS"
description: "Search and read of passages as one function behind the gateway: by meaning through the index when there is one, by keyword otherwise, always returning passage ids the checks can re-read."
version: 0.2.0
status: draft
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Knowledge graph"
part_of: BC-004
realises_capabilities: [CAP-006, CAP-009]
realised_by: [SBB-015]
requires:
  - { abb: ABB-013, cardinality: "0..1", rationale: "Retrieve when the index is configured" }
  - { abb: ABB-002, cardinality: "1", rationale: "Reads passages by id from silver" }
  - { abb: ABB-026, cardinality: "1", rationale: "Fronted by the gateway" }
  - { abb: ABB-027, cardinality: "1", rationale: "Trusts the scope the interceptor wrote" }
domains: [application]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "search_passages (query, collection, limit) and read_passages (up to ten ids) over MCP as the caller (CT-003)" }
  - { id: "I2", direction: "out", type: "query", description: "Passages with ids, text, document and source, filtered by the caller's scope; the method used (vector or keyword)" }
  - { id: "I3", direction: "out", type: "request", description: "Retrieve on the passage index; reads of silver by id" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/tools/gateway.py (passages toolset)", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-025 Passage tools

| Property | Value |
|---|---|
| ABB ID | ABB-025 |
| ABB Name | Passage tools |
| Short Name | PTOOLS |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0, recalibrated to container grain |
| Category | Knowledge graph |
| Bounded context | BC-004 |
| Realises | CAP-006, CAP-009 |
| Realised by | SBB-015 |
| Grain | One C4 container: passes the container test of the [calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md) |

Search and read of passages as one function behind the gateway: by meaning through the index when there is one, by keyword otherwise, always returning passage ids the checks can re-read.

## 1  Purpose

The agent needs two things from passages: find and read. Keeping them in their own container, apart from the graph tools, lets the index be switched off without touching the graph, and lets a search hit always be a citable id.

## 2  Building block

### 2.1  Component Diagram

The components below are the boxes of this container's component diagram, which is not yet drawn. The outside view of this block is its box in [AP-001](../../patterns/AP-001-ontology-driven-graphrag/index.md) and the row of its SBB in [RA-001](../../patterns/RA-001-knowledge-store-on-aws/index.md).

### 2.2  Components

- **Search.** Retrieve on the index, else keyword search over silver, with the method returned
- **Read.** Up to ten passages by id, as the caller
- **Visibility.** The scope rule applied to every passage

### 2.3  Attributes

- **Citability.** Every result is a passage id with its text
- **Degradation.** Keyword fallback when the index is absent

### 2.4  Semantic

Inside: search, read and the filter. Outside: the index (ABB-013) and the lake (ABB-002) it reads, and the gateway that fronts it (ABB-026).

### 2.5  Identity & Access Management

Its own role: Retrieve on the Knowledge Base, the lake's silver prefix. Invoked only by the gateway.

### 2.6  Observability

Per-tool counts, the method used, and latencies in the function's log group.

### 2.7  Governance & Policy Enforcement

The schema is uploaded with the release; the fallback is a stated behaviour, not a silent one.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | request | search_passages (query, collection, limit) and read_passages (up to ten ids) over MCP as the caller (CT-003) |
| I2 | out | query | Passages with ids, text, document and source, filtered by the caller's scope; the method used (vector or keyword) |
| I3 | out | request | Retrieve on the passage index; reads of silver by id |

### 3.4  Capability dependencies (requires)

- ABB-013 (0..1): Retrieve when the index is configured
- ABB-002 (1): Reads passages by id from silver
- ABB-026 (1): Fronted by the gateway
- ABB-027 (1): Trusts the scope the interceptor wrote

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/tools/gateway.py (passages toolset); tools/passages.py` |
| Capabilities | CAP-006, CAP-009 |
| Context | BC-004 |

## 5  Solution Building Block guidance

Realised as a Lambda target of the AgentCore Gateway (SBB-015). The command line runs the same tools in process (ABB-028).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain; new in the calibration |
