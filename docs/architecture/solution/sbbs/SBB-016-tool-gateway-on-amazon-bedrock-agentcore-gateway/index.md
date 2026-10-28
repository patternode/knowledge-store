---
kind: sbb
id: SBB-016
title: "SBB-016 Tool gateway on Amazon Bedrock AgentCore Gateway"
description: "The managed MCP front over the two tool Lambdas: verifies the caller's token, runs the interceptor, routes to the target."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-026]
realised_by_services: []
technologies:
  - { name: "Amazon Bedrock AgentCore Gateway", vendor: "AWS", licensing: "pay per use" }
product_mapping:
  - { abb_component: "Authoriser", technology: "A Cognito JWT authoriser with the tools scope" }
  - { abb_component: "Targets", technology: "The graph and passages Lambdas with their uploaded schemas" }
  - { abb_component: "Interception", technology: "The interceptor Lambda on every call" }
cloud_provider: aws
deployment_model: managed
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-016 Tool gateway on Amazon Bedrock AgentCore Gateway

| Property | Value |
|---|---|
| SBB ID | SBB-016 |
| Realises | ABB-026 |
| Realised by services | none: managed configuration, no code of this repository runs in it |
| Products | Amazon Bedrock AgentCore Gateway |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0, recalibrated to container grain |

The managed MCP front over the two tool Lambdas: verifies the caller's token, runs the interceptor, routes to the target.

## 1  Purpose

One tool surface and one token for the agent, with the authoriser and the interception point managed rather than written. It is a container with no service of this repository behind it: the gateway is configuration, provisioned by the agent module (DN-006).

## 2  Building block

| ABB component | Realised by |
|---|---|
| Authoriser | A Cognito JWT authoriser with the tools scope |
| Targets | The graph and passages Lambdas with their uploaded schemas |
| Interception | The interceptor Lambda on every call |

## 3  Operation

Provisioned by infra/modules/agent; targets re-registered when a schema changes.

## 4  Cost

Per call.

## 5  ABB traceability

ABB-026. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the reference architecture that composes this block with the others is RA-001.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain; new in the calibration |
