---
kind: sbb
id: SBB-005
title: "SBB-005 Tools on AgentCore Gateway with Lambda targets and the interceptor"
description: "The twelve fixed tools as an MCP server the agent calls as the caller, with the scope written into every call by the Gateway's interceptor."
version: 0.1.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-012, ABB-013, ABB-020]
realised_by_services: [tools-graph, tools-passages, agent-interceptor]
products:
  - { name: "Amazon Bedrock AgentCore Gateway", vendor: "AWS", licensing: "pay per use" }
  - { name: "AWS Lambda", vendor: "AWS", licensing: "pay per request" }
product_mapping:
  - { abb_component: "Gateway", sbb_product: "MCP protocol, a Cognito JWT authoriser with the portal's and the service clients allowed, two targets with their schemas from the lake" }
  - { abb_component: "Graph target", sbb_product: "The graph tools Lambda in the private subnets, read-only Neptune" }
  - { abb_component: "Passages target", sbb_product: "The passage tools Lambda outside the VPC, bedrock:Retrieve" }
  - { abb_component: "Interceptor", sbb_product: "A REQUEST interceptor Lambda that writes caller_private from the verified claims" }
cloud_provider: aws
deployment_model: managed
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-005 Tools on AgentCore Gateway with Lambda targets and the interceptor

| Property | Value |
|---|---|
| SBB ID | SBB-005 |
| Realises | ABB-012, ABB-013, ABB-020 |
| Realised by services | tools-graph, tools-passages, agent-interceptor |
| Products | Amazon Bedrock AgentCore Gateway; AWS Lambda |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0 |

The twelve fixed tools as an MCP server the agent calls as the caller, with the scope written into every call by the Gateway's interceptor.

## 1  Purpose

A shared endpoint with a verified token is where scope can be enforced once for every model. The Gateway gives the MCP surface and the interception point; Lambda gives read-only, least-privilege execution per toolset.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Gateway | MCP protocol, a Cognito JWT authoriser with the portal's and the service clients allowed, two targets with their schemas from the lake |
| Graph target | The graph tools Lambda in the private subnets, read-only Neptune |
| Passages target | The passage tools Lambda outside the VPC, bedrock:Retrieve |
| Interceptor | A REQUEST interceptor Lambda that writes caller_private from the verified claims |

## 3  Operation

Tool schemas are generated from the code and uploaded by Terraform; the interceptor's log group is not managed by Terraform.

## 4  Cost

Per call; nothing idle.

## 5  ABB traceability

ABB-012, ABB-013, ABB-020. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the physical pattern that composes this block with the others is REF-001.
