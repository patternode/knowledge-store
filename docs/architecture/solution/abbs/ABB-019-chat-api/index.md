---
kind: abb
id: ABB-019
title: "ABB-019 Chat API"
short_name: "API"
description: "The HTTP API behind the page: quota, asynchronous answering with progress, the index-backed views, drafts and requests for curators, and signed links to documents and tables after the scope check."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Portal"
part_of: BC-006
realises_capabilities: [CAP-009, CAP-010]
realised_by: [SBB-007, SBB-013]
requires:
  - { abb: ABB-020, cardinality: "1", rationale: "Who is asking" }
  - { abb: ABB-014, cardinality: "1", rationale: "Dispatches to the agent" }
  - { abb: ABB-012, cardinality: "1", rationale: "Serves the index-backed routes" }
  - { abb: ABB-002, cardinality: "1", rationale: "Document and table links" }
domains: [application]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "The routes of CT-001 behind the origin check" }
  - { id: "I2", direction: "out", type: "request", description: "Invoke the agent as the person or a service client; self-invoke for the asynchronous half" }
  - { id: "I3", direction: "out", type: "query", description: "Chat state: answers, progress, quotas, usage" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/portal_api/handler.py, state.py, agent_client.py, local.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-019 Chat API

| Property | Value |
|---|---|
| ABB ID | ABB-019 |
| ABB Name | Chat API |
| Short Name | API |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Portal |
| Bounded context | BC-006 |
| Realises | CAP-009, CAP-010 |
| Realised by | SBB-007, SBB-013 |

The HTTP API behind the page: quota, asynchronous answering with progress, the index-backed views, drafts and requests for curators, and signed links to documents and tables after the scope check.

## 1  Purpose

The API is the one door, and it is narrow: bounded inputs, a quota before any model call, an asynchronous answer because the gateway allows thirty seconds, and nothing served to another person.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Routes.** collections, status, summary, ontology, entities, entity, passage, graph, neighbourhood, paths, drafts, draft, table, document, chat, usage, requests
- **Dispatch.** Self-invoke with the job; progress written at most once a second; the page polls
- **Chat state port.** DynamoDB, MongoDB or memory behind one protocol
- **Links.** Presigned for ten minutes after the scope check
- **Local server.** The same handler on loopback with a synthetic private caller

### 2.3  Attributes

- **Boundedness.** Question, search, history and limits clamped before work
- **Fairness.** A refused question costs no model call

### 2.4  Semantic

Inside: routing, state, dispatch, links. Outside: answering and identity.

### 2.5  Identity & Access Management

Reads served prefixes, writes ontology requests, reads and writes the chat table, invokes the chat model and itself, reads two secrets.

### 2.6  Observability

One access log line per request with the caller's subject; generic errors to the caller, full to the log.

### 2.7  Governance & Policy Enforcement

Throttle, reserved concurrency, origin secret, web ACL.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | request | The routes of CT-001 behind the origin check |
| I2 | out | request | Invoke the agent as the person or a service client; self-invoke for the asynchronous half |
| I3 | out | data | Chat state: answers, progress, quotas, usage |

### 3.4  Capability dependencies (requires)

- ABB-020 (1): Who is asking
- ABB-014 (1): Dispatches to the agent
- ABB-012 (1): Serves the index-backed routes
- ABB-002 (1): Document and table links

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/portal_api/handler.py, state.py, agent_client.py, local.py` |
| Capabilities | CAP-009, CAP-010 |
| Context | BC-006 |

## 5  Solution Building Block guidance

Realised as one Lambda behind API Gateway and CloudFront with DynamoDB (SBB-007), or the local server (SBB-013).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
