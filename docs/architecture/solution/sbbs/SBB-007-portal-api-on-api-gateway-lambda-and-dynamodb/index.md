---
kind: sbb
id: SBB-007
title: "SBB-007 Portal API on API Gateway, Lambda and DynamoDB"
description: "The Chat API as one Lambda behind an HTTP API with a DynamoDB table for chat state, quota and usage, reached only through the edge with the origin secret."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-019]
realised_by_services: [portal-api]
technologies:
  - { name: "Amazon API Gateway (HTTP API)", vendor: "AWS", licensing: "pay per request" }
  - { name: "AWS Lambda", vendor: "AWS", licensing: "pay per request" }
  - { name: "Amazon DynamoDB", vendor: "AWS", licensing: "pay per request" }
  - { name: "AWS Secrets Manager", vendor: "AWS", licensing: "per secret" }
product_mapping:
  - { abb_component: "Routes", technology: "ANY /api/{proxy+} on the HTTP API, throttle 20 a second burst 50, access log per request" }
  - { abb_component: "Dispatch", technology: "Self-invocation of the function for asynchronous answering; the result polled" }
  - { abb_component: "Chat state port", technology: "The <name>-chat table with TTLs (ST-011); MongoDB or memory as alternatives" }
  - { abb_component: "Quota", technology: "quota#<sub>#<day> rows taken before dispatch" }
  - { abb_component: "Workbench endpoints and links", technology: "Index-backed views from gold; presigned links into the lake" }
  - { abb_component: "Site grant and secrets", technology: "The service clients' secrets and the origin secret in Secrets Manager (ST-014)" }
  - { abb_component: "Function", technology: "python3.12, 1024 MB, 600 s, reserved concurrency, outside the VPC" }
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
| Products | Amazon API Gateway (HTTP API); AWS Lambda; Amazon DynamoDB; AWS Secrets Manager |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0, recalibrated to container grain |

The Chat API as one Lambda behind an HTTP API with a DynamoDB table for chat state, quota and usage, reached only through the edge with the origin secret.

## 1  Purpose

A function that answers in milliseconds for views and hands the long work to the agent; a table with TTLs for state that expires on its own; an HTTP API because it is cheaper and simpler than REST for one proxy route.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Routes | ANY /api/{proxy+} on the HTTP API, throttle 20 a second burst 50, access log per request |
| Dispatch | Self-invocation of the function for asynchronous answering; the result polled |
| Chat state port | The <name>-chat table with TTLs (ST-011); MongoDB or memory as alternatives |
| Quota | quota#<sub>#<day> rows taken before dispatch |
| Workbench endpoints and links | Index-backed views from gold; presigned links into the lake |
| Site grant and secrets | The service clients' secrets and the origin secret in Secrets Manager (ST-014) |
| Function | python3.12, 1024 MB, 600 s, reserved concurrency, outside the VPC |

## 3  Operation

Reserved concurrency bounds spend; the origin secret rotates with an apply; the table's TTL attribute clears chats after a day.

## 4  Cost

Per request and per table read and write; cents for a small deployment.

## 5  ABB traceability

ABB-019. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the reference architecture that composes this block with the others is RA-001.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain |
