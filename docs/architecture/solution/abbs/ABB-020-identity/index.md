---
kind: abb
id: ABB-020
title: "ABB-020 Identity"
short_name: "IDP"
description: "The identity provider: the people and the service clients, the private-readers group, and the tokens every other container verifies, so that the person's identity goes all the way down (ADR-003)."
version: 0.2.0
status: draft
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Security"
part_of: BC-006
realises_capabilities: [CAP-009]
realised_by: [SBB-008]
requires: []
domains: [technology]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "Sign-in by code flow with PKCE from the page; client credentials from the service clients" }
  - { id: "I2", direction: "out", type: "query", description: "Access tokens with sub, cognito:groups and scopes, verified by the API, the agent and the gateway (CT-012)" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "infra/modules/identity", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-020 Identity

| Property | Value |
|---|---|
| ABB ID | ABB-020 |
| ABB Name | Identity |
| Short Name | IDP |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0, recalibrated to container grain |
| Category | Security |
| Bounded context | BC-006 |
| Realises | CAP-009 |
| Realised by | SBB-008 |
| Grain | One C4 container: passes the container test of the [calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md) |

The identity provider: the people and the service clients, the private-readers group, and the tokens every other container verifies, so that the person's identity goes all the way down (ADR-003).

## 1  Purpose

One issuer, one set of claims, verified at every door. An identity provider is a container by the standard's own verdict: deployed on its own, and every other container talks to it. Scope decisions are not made here; they are made by the interceptor and the API from the claims it issues.

## 2  Building block

### 2.1  Component Diagram

The components below are the boxes of this container's component diagram, which is not yet drawn. The outside view of this block is its box in [PAT-001](../../patterns/PAT-001-ontology-driven-graphrag/index.md) and the row of its SBB in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Components

- **People.** Admin-created users; optional TOTP; the private-readers group
- **Service clients.** The portal's and the evaluation runner's clients with the agent.invoke and tools scopes, their secrets in the secret store
- **Authorisers.** The JWT authorisers the API, the Runtime and the gateway use

### 2.3  Attributes

- **One issuer.** Every token verified against the same pool
- **Optional in site mode.** A host website's grant replaces sign-in; the pool still holds the service clients

### 2.4  Semantic

Inside: people, clients, tokens. Outside: what a token lets a caller see, which is the interceptor (ABB-027) and the API (ABB-019).

### 2.5  Identity & Access Management

The pool is the issuer; clients hold their own secrets; no container reads another's secret.

### 2.6  Observability

Sign-in events in the pool's log; refusals at each authoriser.

### 2.7  Governance & Policy Enforcement

The private group, the scopes and the site roles are deployment inputs.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | request | Sign-in by code flow with PKCE from the page; client credentials from the service clients |
| I2 | out | query | Access tokens with sub, cognito:groups and scopes, verified by the API, the agent and the gateway (CT-012) |

### 3.4  Capability dependencies (requires)

None beyond the cross-cutting trio.

## 4  Mapping

| Where | What |
|---|---|
| Code | `infra/modules/identity; src/knowledge_store/claims.py (the claim names)` |
| Capabilities | CAP-009 |
| Context | BC-006 |

## 5  Solution Building Block guidance

Realised by an Amazon Cognito user pool (SBB-008).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain |
