---
kind: abb
id: ABB-012
title: "ABB-012 Graph tools"
short_name: "GTOOLS"
description: "The fixed, read-only tools over the graph and the bound tables, in the ontology's terms, as one function behind the gateway: no free query reaches a store, and every result is filtered by the caller's scope."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Knowledge graph"
part_of: BC-004
realises_capabilities: [CAP-005, CAP-007, CAP-009]
realised_by: [SBB-005]
requires:
  - { abb: ABB-011, cardinality: "0..1", rationale: "SPARQL when a graph is configured" }
  - { abb: ABB-002, cardinality: "1", rationale: "The gold index and the structured snapshots" }
  - { abb: ABB-026, cardinality: "1", rationale: "Fronted by the gateway" }
  - { abb: ABB-027, cardinality: "1", rationale: "Trusts the scope the interceptor wrote" }
domains: [application]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "The graph and structured tools over MCP as the caller: list_collections, describe_ontology, search_entities, list_entities, get_entity, neighbours, describe, lookup_rows, aggregate (CT-002)" }
  - { id: "I2", direction: "out", type: "query", description: "Results in the ontology's terms, filtered by the caller's scope, each citing its source" }
  - { id: "I3", direction: "out", type: "request", description: "Read-only SPARQL to the knowledge graph; reads of the gold index and snapshots in the lake" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/knowledge_graph/adapters/gateway.py (graph toolset)", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-012 Graph tools

| Property | Value |
|---|---|
| ABB ID | ABB-012 |
| ABB Name | Graph tools |
| Short Name | GTOOLS |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0, recalibrated to container grain |
| Category | Knowledge graph |
| Bounded context | BC-004 |
| Realises | CAP-005, CAP-007, CAP-009 |
| Realised by | SBB-005 |
| Grain | One C4 container: passes the container test of the [calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md) |

The fixed, read-only tools over the graph and the bound tables, in the ontology's terms, as one function behind the gateway: no free query reaches a store, and every result is filtered by the caller's scope.

## 1  Purpose

A model given free SPARQL or Cypher reads what it should not and asks what no one can check (ADR-004). A fixed toolset in the ontology's terms is the one way in, and because it is its own container it can be versioned, scaled and replaced apart from the agent that calls it.

## 2  Building block

### 2.1  Component Diagram

The components below are the boxes of this container's component diagram, which is not yet drawn. The outside view of this block is its box in [AP-001](../../patterns/AP-001-ontology-driven-graphrag/index.md) and the row of its SBB in [RA-001](../../patterns/RA-001-knowledge-store-on-aws/index.md).

### 2.2  Components

- **Collections and ontology.** What exists and what the active version defines
- **Entities.** Search, list and get, in the ontology's terms, from the gold index or the graph
- **Traversal.** Neighbours and paths over the named graphs
- **Structured.** describe, lookup_rows and aggregate over the bound snapshots and metrics
- **Visibility.** The scope rule applied to every result: public, or private to a reader the interceptor marked

### 2.3  Attributes

- **Fixedness.** No tool takes a query string
- **Scope.** Every result passes the visibility filter
- **Statelessness.** Reads only; caches the index for sixty seconds

### 2.4  Semantic

Inside: the tools and the visibility filter. Outside: the gateway that fronts them (ABB-026), the interceptor that marks the caller (ABB-027), and the stores they read.

### 2.5  Identity & Access Management

Its own role: Neptune read, the lake's gold, ontology and config prefixes. Invoked only by the gateway, with the caller's identity in the request.

### 2.6  Observability

Per-tool counts and latencies in the function's log group; refusals logged with reasons.

### 2.7  Governance & Policy Enforcement

The tool schema is uploaded by Terraform with the release; a new tool is a pull request. caller_private is set by the interceptor; a call without it is public.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | request | The graph and structured tools over MCP as the caller: list_collections, describe_ontology, search_entities, list_entities, get_entity, neighbours, describe, lookup_rows, aggregate (CT-002) |
| I2 | out | query | Results in the ontology's terms, filtered by the caller's scope, each citing its source |
| I3 | out | request | Read-only SPARQL to the knowledge graph; reads of the gold index and snapshots in the lake |

### 3.4  Capability dependencies (requires)

- ABB-011 (0..1): SPARQL when a graph is configured
- ABB-002 (1): The gold index and the structured snapshots
- ABB-026 (1): Fronted by the gateway
- ABB-027 (1): Trusts the scope the interceptor wrote

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/knowledge_graph/adapters/gateway.py (graph toolset); portal_api/index.py; graph/sparql.py, traverse.py; structured/query.py` |
| Capabilities | CAP-005, CAP-007, CAP-009 |
| Context | BC-004 |

## 5  Solution Building Block guidance

Realised as a Lambda target of the AgentCore Gateway (SBB-005). The command line runs the same tools in process (ABB-028).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain |
