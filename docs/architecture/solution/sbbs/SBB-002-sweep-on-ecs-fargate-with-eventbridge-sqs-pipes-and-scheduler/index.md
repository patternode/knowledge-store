---
kind: sbb
id: SBB-002
title: "SBB-002 Sweep on ECS Fargate with EventBridge, SQS, Pipes and Scheduler"
description: "The sweep as a Fargate task started by uploads through SQS and Pipes, and by a schedule, with its lock in the lake."
version: 0.1.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-004]
realised_by_services: [pipeline]
products:
  - { name: "Amazon ECS on AWS Fargate", vendor: "AWS", licensing: "pay per task" }
  - { name: "Amazon EventBridge, EventBridge Pipes and Scheduler", vendor: "AWS", licensing: "pay per event" }
  - { name: "Amazon SQS", vendor: "AWS", licensing: "pay per request" }
product_mapping:
  - { abb_component: "Triggers", sbb_product: "An object-created rule on landing/ and ontology/active.json to a queue with a dead-letter queue, a Pipe to RunTask; a rate(6 hours) schedule as the safety net" }
  - { abb_component: "Compute", sbb_product: "A Fargate task, 1 vCPU, 4 GB, 30 GB ephemeral, running the pipeline image :latest with the run command" }
  - { abb_component: "Placement", sbb_product: "Public subnets with egress only by default; private with a NAT when enabled" }
cloud_provider: aws
deployment_model: managed
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-002 Sweep on ECS Fargate with EventBridge, SQS, Pipes and Scheduler

| Property | Value |
|---|---|
| SBB ID | SBB-002 |
| Realises | ABB-004 |
| Realised by services | pipeline |
| Products | Amazon ECS on AWS Fargate; Amazon EventBridge, EventBridge Pipes and Scheduler; Amazon SQS |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0 |

The sweep as a Fargate task started by uploads through SQS and Pipes, and by a schedule, with its lock in the lake.

## 1  Purpose

A task that runs minutes to hours, started by events, with no server to keep: Fargate idles at nothing and the queue absorbs bursts.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Triggers | An object-created rule on landing/ and ontology/active.json to a queue with a dead-letter queue, a Pipe to RunTask; a rate(6 hours) schedule as the safety net |
| Compute | A Fargate task, 1 vCPU, 4 GB, 30 GB ephemeral, running the pipeline image :latest with the run command |
| Placement | Public subnets with egress only by default; private with a NAT when enabled |

## 3  Operation

run_now output starts one by hand; the task log group holds the sweep's log; the dead-letter queue holds uploads that could not start a task.

## 4  Cost

Per task minute while sweeping; nothing idle.

## 5  ABB traceability

ABB-004. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the physical pattern that composes this block with the others is REF-001.
