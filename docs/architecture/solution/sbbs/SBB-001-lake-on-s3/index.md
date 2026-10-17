---
kind: sbb
id: SBB-001
title: "SBB-001 Lake on S3"
description: "One versioned, encrypted, TLS-only S3 bucket as the record, with EventBridge notifications so uploads start the sweep."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-002]
realised_by_services: []
products:
  - { name: "Amazon S3", vendor: "AWS", licensing: "pay per use" }
product_mapping:
  - { abb_component: "Store port", sbb_product: "S3Store over boto3; LocalStore for a folder" }
  - { abb_component: "Layout", sbb_product: "One bucket <name>-lake-<account>, collections under collections/<id>/, landing, kb, locks, config and usage at the root" }
  - { abb_component: "Conditional write", sbb_product: "S3 IfNoneMatch for the sweep lock" }
cloud_provider: aws
deployment_model: managed
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-001 Lake on S3

| Property | Value |
|---|---|
| SBB ID | SBB-001 |
| Realises | ABB-002 |
| Realised by services | None: a managed store, created by the Terraform module. Used by pipeline, portal-api, tools-graph, tools-passages |
| Products | Amazon S3 |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0, recalibrated to container grain |

One versioned, encrypted, TLS-only S3 bucket as the record, with EventBridge notifications so uploads start the sweep.

## 1  Purpose

S3 is the cheapest durable store with conditional writes, versioning and event notifications; the port keeps a folder as the alternative.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Store port | S3Store over boto3; LocalStore for a folder |
| Layout | One bucket <name>-lake-<account>, collections under collections/<id>/, landing, kb, locks, config and usage at the root |
| Conditional write | S3 IfNoneMatch for the sweep lock |

## 3  Operation

Terraform writes collection configuration and tool schemas into it; destroy keeps it unless force_destroy_lake. Old versions expire after thirty days.

## 4  Cost

Storage and requests; cents for a small collection.

## 5  ABB traceability

ABB-002. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the reference architecture that composes this block with the others is RA-001.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain |
