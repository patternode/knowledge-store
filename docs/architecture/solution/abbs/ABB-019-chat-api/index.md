---
kind: abb
id: ABB-019
title: "ABB-019 Chat API"
short_name: "API"
description: "The one HTTP door into the store: it verifies who is asking, takes the quota, dispatches the question to the agent as that person, keeps the answer and the steps, serves the index-backed views, and signs links into the lake."
version: 0.2.0
status: draft
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Portal"
part_of: BC-006
realises_capabilities: [CAP-009, CAP-010, CAP-012]
realised_by: [SBB-007]
requires:
  - { abb: ABB-020, cardinality: "1", rationale: "Verifies tokens or the site grant" }
  - { abb: ABB-014, cardinality: "1", rationale: "Invokes the agent as the person" }
  - { abb: ABB-002, cardinality: "1", rationale: "Reads the served layers, writes requests, signs links" }
domains: [application]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "ANY /api/{proxy+} behind the edge and the origin secret: collections, status, summary, ontology, entities, documents, tables, chat, workbench, requests (CT-001)" }
  - { id: "I2", direction: "out", type: "request", description: "POST /invocations to the agent as the person, with a session id (CT-004)" }
  - { id: "I3", direction: "out", type: "query", description: "Chat state: chats, quota and usage per subject and day (ST-011)" }
  - { id: "I4", direction: "out", type: "query", description: "Signed links into the lake for documents and tables; ontology requests written" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/portal_api/handler.py", ref: "main" }
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
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0, recalibrated to container grain |
| Category | Portal |
| Bounded context | BC-006 |
| Realises | CAP-009, CAP-010, CAP-012 |
| Realised by | SBB-007 |
| Grain | One C4 container: passes the container test of the [calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md) |

The one HTTP door into the store: it verifies who is asking, takes the quota, dispatches the question to the agent as that person, keeps the answer and the steps, serves the index-backed views, and signs links into the lake.

## 1  Purpose

Everything a page needs is behind one narrow API whose every route knows the subject. Quota, chat state, the workbench endpoints, the site grant and the signed links are components of it because they run inside the same function and are not separable.

## 2  Building block

### 2.1  Component Diagram

The components below are the boxes of this container's component diagram, which is not yet drawn. The outside view of this block is its box in [AP-001](../../patterns/AP-001-ontology-driven-graphrag/index.md) and the row of its SBB in [RA-001](../../patterns/RA-001-knowledge-store-on-aws/index.md).

### 2.2  Components

- **Routes.** Every route of CT-001, with the subject on each
- **Dispatch.** Asynchronous answering by self-invocation; polling of the result
- **Chat state port.** DynamoDB, MongoDB or memory behind one port (ST-011)
- **Quota.** Questions per subject per day taken before dispatch; usage recorded after
- **Workbench endpoints.** Steps, prices, term usage and ontology requests for the page's panel
- **Site grant.** X-Site-Grant verified against the host's keys when a host website embeds the page (CT-011)
- **Links.** Presigned document and table links with the subject in the audit trail
- **Fallback loop.** An in-function tool loop used until the agent Runtime exists in a deployment; it lacks the claim-level checks (a finding against ADR-002)

### 2.3  Attributes

- **Narrowness.** One API, no direct store access from a page
- **Subject on every call.** No anonymous route in hosted or site mode

### 2.4  Semantic

Inside: routes, dispatch, state, quota, grant, links. Outside: the agent (ABB-014), the tokens (ABB-020), the page (ABB-018) and the lake (ABB-002).

### 2.5  Identity & Access Management

A Cognito JWT authoriser on the route, or the site grant verified in the function; its own role for the lake's served prefixes, the table, the secrets and the agent's endpoint; no IAM grant to invoke the agent, which the token authorises.

### 2.6  Observability

An access log per request with the subject; the function's log group; usage rows per day.

### 2.7  Governance & Policy Enforcement

Reserved concurrency and the API throttle; the origin secret between the edge and the API; quotas as deployment inputs.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | request | ANY /api/{proxy+} behind the edge and the origin secret: collections, status, summary, ontology, entities, documents, tables, chat, workbench, requests (CT-001) |
| I2 | out | request | POST /invocations to the agent as the person, with a session id (CT-004) |
| I3 | out | query | Chat state: chats, quota and usage per subject and day (ST-011) |
| I4 | out | query | Signed links into the lake for documents and tables; ontology requests written |

### 3.4  Capability dependencies (requires)

- ABB-020 (1): Verifies tokens or the site grant
- ABB-014 (1): Invokes the agent as the person
- ABB-002 (1): Reads the served layers, writes requests, signs links

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/portal_api/handler.py, state.py, agent_client.py, chat.py, local.py; site_grant.py, claims.py; workbench.py (the endpoints)` |
| Capabilities | CAP-009, CAP-010, CAP-012 |
| Context | BC-006 |

## 5  Solution Building Block guidance

Realised as a Lambda behind API Gateway with a DynamoDB table (SBB-007). The command line serves the same API locally (ABB-028).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain |
