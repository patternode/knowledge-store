---
kind: sbb
id: SBB-017
title: "SBB-017 Call interceptor on Lambda"
description: "The interceptor the gateway invokes before every tool call, as one small Lambda with no store access."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-027]
realised_by_services: [agent-interceptor]
products:
  - { name: "AWS Lambda", vendor: "AWS", licensing: "pay per request" }
product_mapping:
  - { abb_component: "Scope rule", sbb_product: "access/adapters/gateway_interceptor.py: sub and cognito:groups, or the site grant's roles, to caller_private" }
  - { abb_component: "Marking", sbb_product: "The argument written into the forwarded call" }
cloud_provider: aws
deployment_model: managed
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-017 Call interceptor on Lambda

| Property | Value |
|---|---|
| SBB ID | SBB-017 |
| Realises | ABB-027 |
| Realised by services | agent-interceptor |
| Products | AWS Lambda |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0, recalibrated to container grain |

The interceptor the gateway invokes before every tool call, as one small Lambda with no store access.

## 1  Purpose

The scope decision in its own function so that no tool reads a token and the rule changes in one place; its log group is one of the two outside Terraform (a finding on SV-006).

## 2  Building block

| ABB component | Realised by |
|---|---|
| Scope rule | access/adapters/gateway_interceptor.py: sub and cognito:groups, or the site grant's roles, to caller_private |
| Marking | The argument written into the forwarded call |

## 3  Operation

python3.12; invoked by the gateway only; no VPC.

## 4  Cost

Per call.

## 5  ABB traceability

ABB-027. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the reference architecture that composes this block with the others is RA-001.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain; new in the calibration |
