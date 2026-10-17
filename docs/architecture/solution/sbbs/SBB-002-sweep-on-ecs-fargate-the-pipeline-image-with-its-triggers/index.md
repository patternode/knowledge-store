---
kind: sbb
id: SBB-002
title: "SBB-002 Sweep on ECS Fargate: the pipeline image with its triggers"
description: "The sweep as one container: the pipeline image (rdflib, pySHACL, pypdf, Claude through the model client) run as a Fargate task, started by uploads through SQS and Pipes and by a schedule, with its lock in the lake."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-004]
realised_by_services: [pipeline]
products:
  - { name: "Amazon ECS on AWS Fargate", vendor: "AWS", licensing: "pay per task" }
  - { name: "Amazon EventBridge, EventBridge Pipes and Scheduler", vendor: "AWS", licensing: "pay per event" }
  - { name: "Amazon SQS", vendor: "AWS", licensing: "pay per request" }
  - { name: "rdflib", vendor: "RDFLib", licensing: "BSD" }
  - { name: "pySHACL", vendor: "RDFLib", licensing: "Apache-2.0" }
  - { name: "pypdf", vendor: "pypdf", licensing: "BSD" }
  - { name: "PyYAML", vendor: "PyYAML", licensing: "MIT" }
  - { name: "boto3", vendor: "AWS", licensing: "Apache-2.0" }
  - { name: "Claude through the model client", vendor: "Anthropic, through Amazon Bedrock or the Anthropic API", licensing: "per token" }
product_mapping:
  - { abb_component: "Triggers", sbb_product: "An object-created rule on landing/ and ontology/active.json to a queue with a dead-letter queue, a Pipe to RunTask; a rate(6 hours) schedule as the safety net" }
  - { abb_component: "Compute", sbb_product: "A Fargate task, 1 vCPU, 4 GB, 30 GB ephemeral, running the pipeline image :latest with the run command" }
  - { abb_component: "Placement", sbb_product: "Public subnets with egress only by default; private with a NAT when enabled" }
  - { abb_component: "Source adapters and refinement", sbb_product: "The built-in adapters, the parsers, the chunker" }
  - { abb_component: "Discovery and review", sbb_product: "rdflib for the draft; the proposal, consolidation and review calls through the model client" }
  - { abb_component: "Extraction and binding", sbb_product: "The tool schema, the extractor, pySHACL validation, N-Quads; snapshots and cells" }
  - { abb_component: "Projection and loading", sbb_product: "The index JSON; the SPARQL, graph-backend and document loaders; the passage sync" }
  - { abb_component: "Model client", sbb_product: "Bedrock in the account's region by default, or the Anthropic API when llm_provider says so, with the key from Secrets Manager; every call wrapped by the ledger" }
cloud_provider: aws
deployment_model: managed
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-002 Sweep on ECS Fargate: the pipeline image with its triggers

| Property | Value |
|---|---|
| SBB ID | SBB-002 |
| Realises | ABB-004 |
| Realised by services | pipeline |
| Products | Amazon ECS on AWS Fargate; Amazon EventBridge, EventBridge Pipes and Scheduler; Amazon SQS; rdflib; pySHACL; pypdf; PyYAML; boto3; Claude through the model client |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0 |

The sweep as one container: the pipeline image (rdflib, pySHACL, pypdf, Claude through the model client) run as a Fargate task, started by uploads through SQS and Pipes and by a schedule, with its lock in the lake.

## 1  Purpose

A task that runs minutes to hours, started by events, with no server to keep: Fargate idles at nothing and the queue absorbs bursts.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Triggers | An object-created rule on landing/ and ontology/active.json to a queue with a dead-letter queue, a Pipe to RunTask; a rate(6 hours) schedule as the safety net |
| Compute | A Fargate task, 1 vCPU, 4 GB, 30 GB ephemeral, running the pipeline image :latest with the run command |
| Placement | Public subnets with egress only by default; private with a NAT when enabled |
| Source adapters and refinement | The built-in adapters, the parsers, the chunker |
| Discovery and review | rdflib for the draft; the proposal, consolidation and review calls through the model client |
| Extraction and binding | The tool schema, the extractor, pySHACL validation, N-Quads; snapshots and cells |
| Projection and loading | The index JSON; the SPARQL, graph-backend and document loaders; the passage sync |
| Model client | Bedrock in the account's region by default, or the Anthropic API when llm_provider says so, with the key from Secrets Manager; every call wrapped by the ledger |

## 3  Operation

run_now output starts one by hand; the task log group holds the sweep's log; the dead-letter queue holds uploads that could not start a task. The image is built by SBB-009 and the task uses :latest, with the aws extra plus the chosen backends.

## 4  Cost

Per task minute while sweeping; nothing idle.

## 5  ABB traceability

ABB-004. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the physical pattern that composes this block with the others is REF-001.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.2.0 | 2026-10-17 | Recalibrated: SBB-014 (the image) merged in, so the container and what it runs are one block; the model client folded in from SBB-012 |
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
