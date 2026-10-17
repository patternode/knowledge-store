---
kind: sbb
id: SBB-015
title: "SBB-015 Passage tools on Lambda behind the AgentCore Gateway"
description: "The passages toolset as one Lambda outside the VPC, registered as a target of the AgentCore Gateway."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-025]
realised_by_services: [tools-passages]
products:
  - { name: "AWS Lambda", vendor: "AWS", licensing: "pay per request" }
  - { name: "Amazon Bedrock AgentCore Gateway (as the front)", vendor: "AWS", licensing: "pay per use" }
product_mapping:
  - { abb_component: "Search", sbb_product: "Retrieve on the Knowledge Base with the collection filter; keyword search over silver when the index is absent; the method returned" }
  - { abb_component: "Read", sbb_product: "read_passages by id from silver, up to ten" }
  - { abb_component: "Visibility", sbb_product: "caller_private honoured on every passage" }
cloud_provider: aws
deployment_model: managed
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-015 Passage tools on Lambda behind the AgentCore Gateway

| Property | Value |
|---|---|
| SBB ID | SBB-015 |
| Realises | ABB-025 |
| Realised by services | tools-passages |
| Products | AWS Lambda; Amazon Bedrock AgentCore Gateway (as the front) |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0, recalibrated to container grain |

The passages toolset as one Lambda outside the VPC, registered as a target of the AgentCore Gateway.

## 1  Purpose

Outside the VPC because it reaches only the Knowledge Base and S3; apart from the graph tools so the index can be switched off without touching the graph.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Search | Retrieve on the Knowledge Base with the collection filter; keyword search over silver when the index is absent; the method returned |
| Read | read_passages by id from silver, up to ten |
| Visibility | caller_private honoured on every passage |

## 3  Operation

python3.12, 1024 MB; the schema at config/tool-schemas; a target on the gateway.

## 4  Cost

Per request plus Retrieve calls; nothing idle.

## 5  ABB traceability

ABB-025. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the physical pattern that composes this block with the others is REF-001.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain; new in the calibration |
