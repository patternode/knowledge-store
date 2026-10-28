---
kind: sbb
id: SBB-008
title: "SBB-008 Identity on Cognito"
description: "Sign-in for people and the token the whole chain verifies, or, in site mode, the service clients the portal uses on a person's behalf."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-020]
realised_by_services: []
technologies:
  - { name: "Amazon Cognito user pools", vendor: "AWS", licensing: "per monthly active user" }
product_mapping:
  - { abb_component: "People", technology: "Admin-created users, a twelve-character password policy, optional TOTP, email recovery; the private-readers group" }
  - { abb_component: "Clients", technology: "A public web client with code flow and PKCE, sixty-minute tokens; in site mode a resource server with agent.invoke, tools.public and tools.private scopes and two client-credentials clients" }
  - { abb_component: "Authorisers", technology: "The pool as issuer for API Gateway, the Runtime and the Gateway" }
cloud_provider: aws
deployment_model: managed
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-008 Identity on Cognito

| Property | Value |
|---|---|
| SBB ID | SBB-008 |
| Realises | ABB-020 |
| Realised by services | none: managed configuration, no code of this repository runs in it |
| Products | Amazon Cognito user pools |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0, recalibrated to container grain |

Sign-in for people and the token the whole chain verifies, or, in site mode, the service clients the portal uses on a person's behalf.

## 1  Purpose

One issuer every hop can verify, groups as the scope carrier, and client credentials for the framed case; no self sign-up by design.

## 2  Building block

| ABB component | Realised by |
|---|---|
| People | Admin-created users, a twelve-character password policy, optional TOTP, email recovery; the private-readers group |
| Clients | A public web client with code flow and PKCE, sixty-minute tokens; in site mode a resource server with agent.invoke, tools.public and tools.private scopes and two client-credentials clients |
| Authorisers | The pool as issuer for API Gateway, the Runtime and the Gateway |

## 3  Operation

Deletion protection off by default so destroy works; turn it on for a long-lived deployment.

## 4  Cost

Free at this scale.

## 5  ABB traceability

ABB-020. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the reference architecture that composes this block with the others is RA-001.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain |
