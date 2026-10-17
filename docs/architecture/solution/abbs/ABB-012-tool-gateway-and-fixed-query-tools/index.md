---
kind: abb
id: ABB-012
title: "ABB-012 Tool gateway and fixed query tools"
short_name: "TOOLS"
description: "Twelve read-only tools in the ontology's terms, offered to agents through one gateway whose interceptor sets the caller's scope on every call from the verified token, over the graph, the tables and the passages. The same functions run in process for the chat API's fallback and the local agent."
version: 0.2.0
status: draft
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Knowledge graph"
part_of: BC-004
realises_capabilities: [CAP-005, CAP-007, CAP-009]
realised_by: [SBB-005]
requires:
  - { abb: ABB-011, cardinality: "1", rationale: "The graph it queries" }
  - { abb: ABB-013, cardinality: "0..1", rationale: "The passage index, with a keyword fallback when it is off" }
  - { abb: ABB-020, cardinality: "1", rationale: "The token the gateway verifies and the rule that reads scope from it" }
  - { abb: ABB-002, cardinality: "1", rationale: "Silver, the index, snapshots and cells" }
domains: [application, data]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "A tool name and arguments, with caller_private (CT-002)" }
  - { id: "I2", direction: "out", type: "query", description: "Entities, views, neighbourhoods, paths, tables, rows, figures; the collections and the ontology rendition" }
  - { id: "I3", direction: "in", type: "query", description: "The index, the SPARQL store, the backends, the structured snapshots" }
  - { id: "I4", direction: "in", type: "request", description: "tools/list and tools/call over MCP as the caller, with the verified token" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/tools/gateway.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-012 Tool gateway and fixed query tools

| Property | Value |
|---|---|
| ABB ID | ABB-012 |
| ABB Name | Tool gateway and fixed query tools |
| Short Name | TOOLS |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Knowledge graph |
| Bounded context | BC-004 |
| Realises | CAP-005, CAP-007, CAP-009 |
| Realised by | SBB-005 |

Twelve read-only tools in the ontology's terms, offered to agents through one gateway whose interceptor sets the caller's scope on every call from the verified token, over the graph, the tables and the passages. The same functions run in process for the chat API's fallback and the local agent.

## 1  Purpose

The agent never writes a query. Fixed tools make scope enforceable at a shared endpoint, make every answer explainable as a tool call, and keep the model from reaching the stores directly.

## 2  Building block

### 2.1  Component Diagram

The components below are what runs inside this one container, listed per the building block calibration standard: none of them is a building block of its own. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Gateway.** The MCP front: a JWT authoriser with the portal's and the service clients allowed, two targets with their schemas from the lake
- **Interceptor.** Decodes the verified bearer on every tools/call and overwrites caller_private from its claims, whatever the model wrote
- **Collections and ontology.** list_collections, describe_ontology
- **Entities.** search_entities, list_entities, get_entity with passages
- **Traversal.** neighbourhood with hops, find_paths up to four, over Adjacency
- **Structured.** describe_structured, lookup_rows, aggregate with figure ids
- **Passages.** Retrieve with the collection and scope filters, re-checked against metadata; a tf-idf fallback over the index when the passage index is off; read by id from the projection, then silver
- **Visibility.** visible, public names, per-graph scope in SPARQL, filters in the backends

### 2.3  Attributes

- **Scope safety.** Only a literal true caller_private is private; without the interceptor a caller is public
- **Boundedness.** Every argument clamped; result text capped
- **Portability.** One implementation, three surfaces

### 2.4  Semantic

Inside: the gateway, the scope it enforces, and the tool functions. Outside: the stores the tools read, the agent that calls them, and the identities the token comes from.

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
| I4 | in | request | tools/list and tools/call over MCP as the caller, with the verified token |

### 3.4  Capability dependencies (requires)

- ABB-011 (1): The graph it queries
- ABB-013 (0..1): The passage index, with a keyword fallback when it is off
- ABB-020 (1): The token the gateway verifies and the rule that reads scope from it
- ABB-002 (1): Silver, the index, snapshots and cells

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/tools/gateway.py, passages.py, interceptor.py; graph/sparql.py, traverse.py; structured/query.py; portal_api/index.py` |
| Capabilities | CAP-005, CAP-007, CAP-009 |
| Context | BC-004 |

## 5  Solution Building Block guidance

Realised as AgentCore Gateway with two Lambda targets and the interceptor (SBB-005). The same functions run inside the chat API (ABB-019) as its fallback and in process on an operator's machine (SBB-015).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.2.0 | 2026-10-17 | Recalibrated to container grain: the gateway and its interceptor (from ABB-020) and the passage tools (from ABB-013) folded in; renamed from Fixed query tools |
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
