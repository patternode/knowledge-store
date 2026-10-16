---
kind: sbb
id: SBB-007
title: "SBB-007 Portal on CloudFront, API Gateway, Lambda and DynamoDB"
description: "The page and its API on one URL, serverless end to end, with the chat state and quotas in one on-demand table."
version: 0.1.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-018, ABB-019, ABB-016, ABB-017, ABB-012, ABB-014, ABB-020]
realised_by_services: [portal-api, chat-page]
products:
  - { name: "Amazon CloudFront", vendor: "AWS", licensing: "per request" }
  - { name: "Amazon API Gateway (HTTP API)", vendor: "AWS", licensing: "per request" }
  - { name: "AWS Lambda", vendor: "AWS", licensing: "per request" }
  - { name: "Amazon DynamoDB", vendor: "AWS", licensing: "on demand" }
  - { name: "AWS Secrets Manager", vendor: "AWS", licensing: "per secret" }
product_mapping:
  - { abb_component: "Edge", sbb_product: "CloudFront serving the page from a private bucket through origin access control and /api/* to the API with an origin secret header; managed security headers; an optional web ACL and custom domain" }
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

# SBB-007 Portal on CloudFront, API Gateway, Lambda and DynamoDB

| Property | Value |
|---|---|
| SBB ID | SBB-007 |
| Realises | ABB-018, ABB-019, ABB-016, ABB-017, ABB-012, ABB-014, ABB-020 |
| Realised by services | portal-api, chat-page |
| Products | Amazon CloudFront; Amazon API Gateway (HTTP API); AWS Lambda; Amazon DynamoDB; AWS Secrets Manager |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0 |

The page and its API on one URL, serverless end to end, with the chat state and quotas in one on-demand table.

## 1  Purpose

Pay per request end to end; the gateway's thirty-second limit is why answers are asynchronous; DynamoDB's conditional write is what makes the quota hold under concurrency.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Edge | CloudFront serving the page from a private bucket through origin access control and /api/* to the API with an origin secret header; managed security headers; an optional web ACL and custom domain |
| API | One ANY /api/{proxy+} route with a Cognito JWT authoriser (none in site mode), throttled, access-logged |
| Lambda | The portal API handler with reserved concurrency as the chat valve; the fallback Converse loop; self-invocation for asynchronous answers |
| State | DynamoDB <name>-chat with pk and a TTL: chat#, quota#, usage#, agent# keys |
| Secrets | Service clients for site mode; the Anthropic key when chosen |

## 3  Operation

chat_concurrency 0 turns the chat off; the API answers with its own loop until the Runtime exists.

## 4  Cost

Close to nothing idle.

## 5  ABB traceability

ABB-018, ABB-019, ABB-016, ABB-017, ABB-012, ABB-014, ABB-020. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the physical pattern that composes this block with the others is REF-001.
