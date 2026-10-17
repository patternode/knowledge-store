---
kind: abb
id: ABB-020
title: "ABB-020 Identity"
short_name: "IDENT"
description: "Who the caller is and whether they may read private content, decided from a verified token by one rule: sign-in for people, the groups and scopes in the token, the service clients a host website uses on a person's behalf, and the site grant. Every container that verifies a token applies the rule; the gateway's interceptor (ABB-012) makes it true for the tools whatever the model wrote."
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
domains: [application, technology]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "A Cognito access token (sub, groups, scope) or a host website's ES256 grant (sub, roles) (CT-011, CT-012)" }
  - { id: "I2", direction: "out", type: "event", description: "sub and private for the caller; caller_private on every tool call" }
  - { id: "I3", direction: "out", type: "request", description: "Allowed clients for the Runtime and the Gateway" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/claims.py, site_grant.py, tools/interceptor.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-020 Identity

| Property | Value |
|---|---|
| ABB ID | ABB-020 |
| ABB Name | Identity |
| Short Name | IDENT |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Security |
| Bounded context | BC-006 |
| Realises | CAP-009 |
| Realised by | SBB-008 |

Who the caller is and whether they may read private content, decided from a verified token by one rule: sign-in for people, the groups and scopes in the token, the service clients a host website uses on a person's behalf, and the site grant. Every container that verifies a token applies the rule; the gateway's interceptor (ABB-012) makes it true for the tools whatever the model wrote.

## 1  Purpose

The person's identity goes all the way down (ADR-003). One function says what private means; every hop reads it from the token it verified, and no service identity in the chat path can read more than the person.

## 2  Building block

### 2.1  Component Diagram

The components below are what runs inside this one container, listed per the building block calibration standard: none of them is a building block of its own. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Scope rule.** claims.py: subject, private reader by group, private caller by group or scope
- **Sign-in.** Code flow with PKCE; admin-created users; the private-readers group; resource-server scopes and two service clients for site mode
- **Site grant.** ES256 verified with the standard library against configured keys: issuer, audience, expiry, roles
- **Service clients.** Public and private client credentials the portal uses in site mode

### 2.3  Attributes

- **Fail closed.** A token without a subject is refused; without the interceptor a caller is public
- **No minting.** The portal verifies grants and never issues them

### 2.4  Semantic

Inside: identities, tokens and the rule that reads them. Outside: applying the rule at the gateway (ABB-012), the API (ABB-019) and the agent (ABB-014).

### 2.5  Identity & Access Management

It is the IAM of the people; the roles of the services are in each service's page.

### 2.6  Observability

Refusals logged with reasons; the access log carries the subject.

### 2.7  Governance & Policy Enforcement

The private group, the scopes and the site roles are deployment inputs; the rule is code.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | token | A Cognito access token (sub, groups, scope) or a host website's ES256 grant (sub, roles) (CT-011, CT-012) |
| I2 | out | decision | sub and private for the caller; caller_private on every tool call |
| I3 | out | config | Allowed clients for the Runtime and the Gateway |

### 3.4  Capability dependencies (requires)

None beyond the cross-cutting trio.

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/claims.py, site_grant.py; infra/modules/identity` |
| Capabilities | CAP-009 |
| Context | BC-006 |

## 5  Solution Building Block guidance

Realised by Cognito (SBB-008); the claims rule is a library every verifying container carries, and the interceptor that applies it to the tools belongs to the gateway (SBB-005).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.2.0 | 2026-10-17 | Recalibrated to container grain: the interceptor moved to ABB-012; the block is the identity provider and its rule; renamed from Identity and scope |
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
