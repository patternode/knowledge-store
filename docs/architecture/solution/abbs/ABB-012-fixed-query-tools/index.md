---
kind: abb
id: ABB-012
title: "ABB-012 Fixed query tools"
short_name: "TOOLS"
description: "Twelve read-only tools the store defines in the ontology's terms, the same functions behind the Gateway, the portal and the local agent, every result filtered to what the caller may see."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Knowledge graph"
part_of: BC-004
realises_capabilities: [CAP-005, CAP-007, CAP-009]
realised_by: [SBB-005, SBB-007, SBB-013]
requires:
  - { abb: ABB-011, cardinality: "1", rationale: "The projections it reads" }
  - { abb: ABB-020, cardinality: "1", rationale: "The caller's scope, set by the interceptor" }
domains: [application, data]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "A tool name and arguments, with caller_private (CT-002)" }
  - { id: "I2", direction: "out", type: "query", description: "Entities, views, neighbourhoods, paths, tables, rows, figures; the collections and the ontology rendition" }
  - { id: "I3", direction: "in", type: "query", description: "The index, the SPARQL store, the backends, the structured snapshots" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/tools/gateway.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-012 Fixed query tools

| Property | Value |
|---|---|
| ABB ID | ABB-012 |
| ABB Name | Fixed query tools |
| Short Name | TOOLS |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Knowledge graph |
| Bounded context | BC-004 |
| Realises | CAP-005, CAP-007, CAP-009 |
| Realised by | SBB-005, SBB-007, SBB-013 |

Twelve read-only tools the store defines in the ontology's terms, the same functions behind the Gateway, the portal and the local agent, every result filtered to what the caller may see.

## 1  Purpose

The agent never writes a query. Fixed tools make scope enforceable at a shared endpoint, make every answer explainable as a tool call, and keep the model from reaching the stores directly.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Collections and ontology.** list_collections, describe_ontology
- **Entities.** search_entities, list_entities, get_entity with passages
- **Traversal.** neighbourhood with hops, find_paths up to four, over Adjacency
- **Structured.** describe_structured, lookup_rows, aggregate with figure ids
- **Visibility.** visible, public names, per-graph scope in SPARQL, filters in the backends

### 2.3  Attributes

- **Scope safety.** Only a literal true caller_private is private; without the interceptor a caller is public
- **Boundedness.** Every argument clamped; result text capped
- **Portability.** One implementation, three surfaces

### 2.4  Semantic

Inside: the tools and their filtering. Outside: who calls them (the agent) and what identity means (ABB-020).

### 2.5  Identity & Access Management

The graph tools Lambda reads Neptune with a read-only role and sits in the private subnets; the passage tools Lambda calls Retrieve; neither writes.

### 2.6  Observability

Each call is a step in the workbench with its source (graph, structured, vector, keyword).

### 2.7  Governance & Policy Enforcement

No free SPARQL or Cypher (ADR-004).

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | request | A tool name and arguments, with caller_private (CT-002) |
| I2 | out | result | Entities, views, neighbourhoods, paths, tables, rows, figures; the collections and the ontology rendition |
| I3 | in | data | The index, the SPARQL store, the backends, the structured snapshots |

### 3.4  Capability dependencies (requires)

- ABB-011 (1): The projections it reads
- ABB-020 (1): The caller's scope, set by the interceptor

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/tools/gateway.py; portal_api/index.py; graph/sparql.py, traverse.py; structured/query.py` |
| Capabilities | CAP-005, CAP-007, CAP-009 |
| Context | BC-004 |

## 5  Solution Building Block guidance

Realised behind AgentCore Gateway (SBB-005), inside the portal Lambda (SBB-007) and in process locally (SBB-013).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
