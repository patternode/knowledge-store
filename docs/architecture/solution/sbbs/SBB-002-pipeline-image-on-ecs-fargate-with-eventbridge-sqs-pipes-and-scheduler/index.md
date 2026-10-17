---
kind: sbb
id: SBB-002
title: "SBB-002 Pipeline image on ECS Fargate with EventBridge, SQS, Pipes and Scheduler"
description: "The pipeline as one image, built in the account from the deployed source, run as a Fargate task started by uploads through SQS and Pipes and by a schedule, with its lock in the lake."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-024]
realised_by_services: [pipeline]
products:
  - { name: "Amazon ECS on AWS Fargate", vendor: "AWS", licensing: "pay per task" }
  - { name: "Amazon EventBridge, EventBridge Pipes and Scheduler", vendor: "AWS", licensing: "pay per event" }
  - { name: "Amazon SQS", vendor: "AWS", licensing: "pay per request" }
  - { name: "rdflib, pySHACL, pypdf, PyYAML, boto3", vendor: "open source", licensing: "permissive" }
  - { name: "Claude through the model client", vendor: "AWS Bedrock or Anthropic", licensing: "per token" }
product_mapping:
  - { abb_component: "Stages in order", sbb_product: "The knowledge_store package in the image: adapters, refine, ontology discovery, review and versions, extract, structured binding, project, graph loaders, the passage sync, the ledger client" }
  - { abb_component: "Lock and rounds", sbb_product: "locks/pipeline.json by conditional write; rounds until nothing changes" }
  - { abb_component: "Triggers", sbb_product: "An object-created rule on landing/ and ontology/active.json to a queue with a dead-letter queue, a Pipe to RunTask; a rate(6 hours) schedule as the safety net (DN-016)" }
  - { abb_component: "Compute", sbb_product: "A Fargate task, 1 vCPU, 4 GB, 30 GB ephemeral, arm64 or x86 as built, in the private subnets (DN-004)" }
  - { abb_component: "Model", sbb_product: "Bedrock in the region with grants scoped to the configured ids, or the Anthropic API with its key from the secret store; prices from the ledger's table" }
cloud_provider: aws
deployment_model: managed
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-002 Pipeline image on ECS Fargate with EventBridge, SQS, Pipes and Scheduler

| Property | Value |
|---|---|
| SBB ID | SBB-002 |
| Realises | ABB-024 |
| Realised by services | pipeline |
| Products | Amazon ECS on AWS Fargate; Amazon EventBridge, EventBridge Pipes and Scheduler; Amazon SQS; rdflib, pySHACL, pypdf, PyYAML, boto3; Claude through the model client |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0, recalibrated to container grain |

The pipeline as one image, built in the account from the deployed source, run as a Fargate task started by uploads through SQS and Pipes and by a schedule, with its lock in the lake.

## 1  Purpose

A task that runs minutes to hours, started by events, with no server to keep: Fargate idles at nothing and the queue absorbs bursts. One image holds every stage because the stages share the lake layout and the ontology parser; the cost is that four contexts ship together (CN-006).

## 2  Building block

| ABB component | Realised by |
|---|---|
| Stages in order | The knowledge_store package in the image: adapters, refine, ontology discovery, review and versions, extract, structured binding, project, graph loaders, the passage sync, the ledger client |
| Lock and rounds | locks/pipeline.json by conditional write; rounds until nothing changes |
| Triggers | An object-created rule on landing/ and ontology/active.json to a queue with a dead-letter queue, a Pipe to RunTask; a rate(6 hours) schedule as the safety net (DN-016) |
| Compute | A Fargate task, 1 vCPU, 4 GB, 30 GB ephemeral, arm64 or x86 as built, in the private subnets (DN-004) |
| Model | Bedrock in the region with grants scoped to the configured ids, or the Anthropic API with its key from the secret store; prices from the ledger's table |

## 3  Operation

run_now output starts one by hand; the task log group holds the sweep's log; the dead-letter queue holds uploads that could not start a task; the image is rebuilt by CodeBuild when the source changes (DN-013, ST-017).

## 4  Cost

Per task minute while sweeping, plus model calls per document per version; nothing idle.

## 5  ABB traceability

ABB-024. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the reference architecture that composes this block with the others is REF-001.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain |
