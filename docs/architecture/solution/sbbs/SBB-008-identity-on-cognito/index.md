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
realised_by_services: [chat-page, portal-api]
products:
  - { name: "Amazon Cognito user pools", vendor: "AWS", licensing: "per monthly active user" }
product_mapping:
  - { abb_component: "People", sbb_product: "Admin-created users, a twelve-character password policy, optional TOTP, email recovery; the private-readers group" }
  - { abb_component: "Clients", sbb_product: "A public web client with code flow and PKCE, sixty-minute tokens; in site mode a resource server with agent.invoke, tools.public and tools.private scopes and two client-credentials clients" }
  - { abb_component: "Authorisers", sbb_product: "The pool as issuer for API Gateway, the Runtime and the Gateway" }
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
| Realised by services | chat-page, portal-api |
| Products | Amazon Cognito user pools |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0 |

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

ABB-020. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the physical pattern that composes this block with the others is REF-001.
