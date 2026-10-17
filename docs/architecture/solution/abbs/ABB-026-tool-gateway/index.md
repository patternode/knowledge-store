---
kind: abb
id: ABB-026
title: "ABB-026 Tool gateway"
short_name: "GW"
description: "The one MCP front over the tools: it verifies the caller's token, runs the interceptor on every call, and routes to the graph tools or the passage tools, so that the agent never addresses a function directly."
version: 0.2.0
status: draft
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Knowledge graph"
part_of: BC-004
realises_capabilities: [CAP-009]
realised_by: [SBB-016]
requires:
  - { abb: ABB-020, cardinality: "1", rationale: "Verifies the caller's token against the identity provider" }
  - { abb: ABB-027, cardinality: "1", rationale: "Runs the interceptor on every call" }
domains: [technology]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "MCP over HTTPS with the caller's bearer token: the graph and passage tools (CT-002, CT-003)" }
  - { id: "I2", direction: "out", type: "request", description: "The call forwarded to the graph tools or the passage tools, after the interceptor" }
  - { id: "I3", direction: "out", type: "request", description: "Token verification against the identity provider (CT-012)" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "infra/modules/agent (gateway", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-026 Tool gateway

| Property | Value |
|---|---|
| ABB ID | ABB-026 |
| ABB Name | Tool gateway |
| Short Name | GW |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0, recalibrated to container grain |
| Category | Knowledge graph |
| Bounded context | BC-004 |
| Realises | CAP-009 |
| Realised by | SBB-016 |
| Grain | One C4 container: passes the container test of the [calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md) |

The one MCP front over the tools: it verifies the caller's token, runs the interceptor on every call, and routes to the graph tools or the passage tools, so that the agent never addresses a function directly.

## 1  Purpose

An agent should see one tool surface and present one token; the containers behind it should be free to change. A managed gateway gives the authoriser, the routing and the interception point without a server to run. It is a container by the standard's own worked verdict: an API gateway is deployed on its own and swappable.

## 2  Building block

### 2.1  Component Diagram

The components below are the boxes of this container's component diagram, which is not yet drawn. The outside view of this block is its box in [AP-001](../../patterns/AP-001-ontology-driven-graphrag/index.md) and the row of its SBB in [RA-001](../../patterns/RA-001-knowledge-store-on-aws/index.md).

### 2.2  Components

- **Authoriser.** A JWT authoriser against the identity provider; the scopes a client may hold
- **Targets.** The graph toolset and the passages toolset, each a function with its uploaded schema
- **Interception.** The interceptor invoked before every target

### 2.3  Attributes

- **One surface.** Every tool reachable through one endpoint
- **Managed.** No server; pay per call

### 2.4  Semantic

Inside: verification, interception, routing. Outside: the tools themselves and the identity provider.

### 2.5  Identity & Access Management

The gateway role invokes the two targets and the interceptor; callers present a Cognito access token with the tools scope.

### 2.6  Observability

Per-call logs with the caller's subject; latencies per target.

### 2.7  Governance & Policy Enforcement

Targets and schemas are provisioned with the release; the gateway accepts tokens from the deployment's own pool only.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | request | MCP over HTTPS with the caller's bearer token: the graph and passage tools (CT-002, CT-003) |
| I2 | out | request | The call forwarded to the graph tools or the passage tools, after the interceptor |
| I3 | out | request | Token verification against the identity provider (CT-012) |

### 3.4  Capability dependencies (requires)

- ABB-020 (1): Verifies the caller's token against the identity provider
- ABB-027 (1): Runs the interceptor on every call

## 4  Mapping

| Where | What |
|---|---|
| Code | `infra/modules/agent (gateway, targets, interceptor wiring)` |
| Capabilities | CAP-009 |
| Context | BC-004 |

## 5  Solution Building Block guidance

Realised by Amazon Bedrock AgentCore Gateway (SBB-016).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain; new in the calibration |
