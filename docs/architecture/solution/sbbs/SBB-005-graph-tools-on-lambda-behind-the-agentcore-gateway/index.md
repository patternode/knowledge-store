---
kind: sbb
id: SBB-005
title: "SBB-005 Graph tools on Lambda behind the AgentCore Gateway"
description: "The graph and structured toolset as one Lambda in the private subnets, registered as a target of the AgentCore Gateway with its schema uploaded by Terraform."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-012]
realised_by_services: [tools-graph]
technologies:
  - { name: "AWS Lambda", vendor: "AWS", licensing: "pay per request" }
  - { name: "Amazon Bedrock AgentCore Gateway (as the front)", vendor: "AWS", licensing: "pay per use" }
product_mapping:
  - { abb_component: "Collections and ontology", technology: "The toolset's list and describe tools over the lake's config and ontology prefixes" }
  - { abb_component: "Entities", technology: "search, list and get over the gold index, cached sixty seconds" }
  - { abb_component: "Traversal", technology: "neighbours over SPARQL to Neptune with SigV4, thirty-second timeout" }
  - { abb_component: "Structured", technology: "describe, lookup_rows and aggregate over the snapshots in gold" }
  - { abb_component: "Visibility", technology: "caller_private honoured on every result" }
cloud_provider: aws
deployment_model: managed
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-005 Graph tools on Lambda behind the AgentCore Gateway

| Property | Value |
|---|---|
| SBB ID | SBB-005 |
| Realises | ABB-012 |
| Realised by services | tools-graph |
| Products | AWS Lambda; Amazon Bedrock AgentCore Gateway (as the front) |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0, recalibrated to container grain |

The graph and structured toolset as one Lambda in the private subnets, registered as a target of the AgentCore Gateway with its schema uploaded by Terraform.

## 1  Purpose

A function per toolset: the graph tools need the VPC for Neptune, the passage tools do not, and each scales and deploys alone. The gateway, not the function, holds the authoriser.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Collections and ontology | The toolset's list and describe tools over the lake's config and ontology prefixes |
| Entities | search, list and get over the gold index, cached sixty seconds |
| Traversal | neighbours over SPARQL to Neptune with SigV4, thirty-second timeout |
| Structured | describe, lookup_rows and aggregate over the snapshots in gold |
| Visibility | caller_private honoured on every result |

## 3  Operation

python3.12, 1024 MB, in the private subnets; the schema at config/tool-schemas in the lake; a target on the gateway.

## 4  Cost

Per request; nothing idle.

## 5  ABB traceability

ABB-012. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the reference architecture that composes this block with the others is RA-001.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain |
