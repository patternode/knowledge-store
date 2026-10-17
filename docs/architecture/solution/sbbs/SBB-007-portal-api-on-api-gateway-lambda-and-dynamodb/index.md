---
kind: sbb
id: SBB-007
title: "SBB-007 Portal API on API Gateway, Lambda and DynamoDB"
description: "The chat API behind the page, reached through the same CloudFront distribution as the page: one Lambda behind an HTTP API, with the chat state and quotas in one on-demand table."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-019]
realised_by_services: [portal-api]
products:
  - { name: "Amazon CloudFront", vendor: "AWS", licensing: "per request" }
  - { name: "Amazon API Gateway (HTTP API)", vendor: "AWS", licensing: "per request" }
  - { name: "AWS Lambda", vendor: "AWS", licensing: "per request" }
  - { name: "Amazon DynamoDB", vendor: "AWS", licensing: "on demand" }
  - { name: "AWS Secrets Manager", vendor: "AWS", licensing: "per secret" }
product_mapping:
  - { abb_component: "Edge", sbb_product: "CloudFront routes /api/* to the API with an origin secret header, on the same URL as the page (SBB-016)" }
  - { abb_component: "API", sbb_product: "One ANY /api/{proxy+} route with a Cognito JWT authoriser (none in site mode), throttled, access-logged" }
  - { abb_component: "Lambda", sbb_product: "The portal API handler with reserved concurrency as the chat valve; the fallback Converse loop; self-invocation for asynchronous answers" }
  - { abb_component: "State", sbb_product: "DynamoDB <name>-chat with pk and a TTL: chat#, quota#, usage#, agent# keys" }
  - { abb_component: "Secrets", sbb_product: "Service clients for site mode; the Anthropic key when chosen" }
cloud_provider: aws
deployment_model: managed
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-007 Portal API on API Gateway, Lambda and DynamoDB

| Property | Value |
|---|---|
| SBB ID | SBB-007 |
| Realises | ABB-019 |
| Realised by services | portal-api |
| Products | Amazon CloudFront; Amazon API Gateway (HTTP API); AWS Lambda; Amazon DynamoDB; AWS Secrets Manager |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0 |

The chat API behind the page, reached through the same CloudFront distribution as the page: one Lambda behind an HTTP API, with the chat state and quotas in one on-demand table.

## 1  Purpose

Pay per request end to end; the gateway's thirty-second limit is why answers are asynchronous; DynamoDB's conditional write is what makes the quota hold under concurrency.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Edge | CloudFront routes /api/* to the API with an origin secret header, on the same URL as the page (SBB-016) |
| API | One ANY /api/{proxy+} route with a Cognito JWT authoriser (none in site mode), throttled, access-logged |
| Lambda | The portal API handler with reserved concurrency as the chat valve; the fallback Converse loop; self-invocation for asynchronous answers |
| State | DynamoDB <name>-chat with pk and a TTL: chat#, quota#, usage#, agent# keys |
| Secrets | Service clients for site mode; the Anthropic key when chosen |

## 3  Operation

chat_concurrency 0 turns the chat off; the API answers with its own loop until the Runtime exists.

## 4  Cost

Close to nothing idle.

## 5  ABB traceability

ABB-019. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the physical pattern that composes this block with the others is REF-001.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.2.0 | 2026-10-17 | Recalibrated: the chat page split out as SBB-016, so this block is the API container alone |
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
