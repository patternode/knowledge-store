---
kind: abb
id: ABB-027
title: "ABB-027 Call interceptor"
short_name: "ICPT"
description: "The function the gateway runs on every tool call, which turns the caller's identity into the one access decision the store makes today: whether private sources are visible (ADR-010)."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Security"
part_of: BC-006
realises_capabilities: [CAP-009]
realised_by: [SBB-017]
requires:
  - { abb: ABB-020, cardinality: "1", rationale: "Reads the groups and scopes the identity provider put in the token" }
domains: [application]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "Every tool call from the gateway, with the caller's token claims" }
  - { id: "I2", direction: "out", type: "request", description: "The same call with caller_private set when the caller may read private sources; otherwise the call as public" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/access/adapters/gateway_interceptor.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-027 Call interceptor

| Property | Value |
|---|---|
| ABB ID | ABB-027 |
| ABB Name | Call interceptor |
| Short Name | ICPT |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0, recalibrated to container grain |
| Category | Security |
| Bounded context | BC-006 |
| Realises | CAP-009 |
| Realised by | SBB-017 |
| Grain | One C4 container: passes the container test of the [calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md) |

The function the gateway runs on every tool call, which turns the caller's identity into the one access decision the store makes today: whether private sources are visible (ADR-010).

## 1  Purpose

Scope is decided once, in one place, before any tool runs, from the token and nothing else. Keeping it in its own container, apart from the tools, means the tools trust a mark they never compute and the rule changes in one place.

## 2  Building block

### 2.1  Component Diagram

The components below are the boxes of this container's component diagram, which is not yet drawn. The outside view of this block is its box in [AP-001](../../patterns/AP-001-ontology-driven-graphrag/index.md) and the row of its SBB in [RA-001](../../patterns/RA-001-knowledge-store-on-aws/index.md).

### 2.2  Components

- **Scope rule.** sub and cognito:groups, or the site grant's roles, to caller_private
- **Marking.** The argument written into the call the tools receive; a call without it is public

### 2.3  Attributes

- **Single decision point.** No tool reads a token
- **Fail closed.** An unreadable token is public

### 2.4  Semantic

Inside: the rule and the mark. Outside: the tokens (ABB-020) and the tools that honour the mark (ABB-012, ABB-025).

### 2.5  Identity & Access Management

Its own role with no store access; invoked only by the gateway.

### 2.6  Observability

Decisions logged with the subject; refusals with reasons.

### 2.7  Governance & Policy Enforcement

The private group and the site roles are deployment inputs; the rule is code.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | request | Every tool call from the gateway, with the caller's token claims |
| I2 | out | request | The same call with caller_private set when the caller may read private sources; otherwise the call as public |

### 3.4  Capability dependencies (requires)

- ABB-020 (1): Reads the groups and scopes the identity provider put in the token

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/access/adapters/gateway_interceptor.py; claims.py` |
| Capabilities | CAP-009 |
| Context | BC-006 |

## 5  Solution Building Block guidance

Realised as a Lambda interceptor on the AgentCore Gateway (SBB-017).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain; new in the calibration |
