---
kind: abb
id: ABB-004
title: "ABB-004 Sweep orchestration"
short_name: "SWEEP"
description: "One idempotent pass over every collection and stage, under a lock, repeated until a round changes nothing, started by uploads and backed by a schedule."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Ingestion"
part_of: BC-001
realises_capabilities: [CAP-002]
realised_by: [SBB-002, SBB-013]
requires:
  - { abb: ABB-002, cardinality: "1", rationale: "The lock and the status live in the lake" }
  - { abb: ABB-006, cardinality: "1", rationale: "Publishes a provided ontology and auto-publishes a draft" }
  - { abb: ABB-009, cardinality: "1", rationale: "Runs extraction" }
  - { abb: ABB-011, cardinality: "1", rationale: "Runs projection and loading" }
domains: [application]
interfaces:
  - { id: "I1", direction: "in", type: "event", description: "An upload event, a schedule, or a command" }
  - { id: "I2", direction: "out", type: "event", description: "portal/status.json per collection: stage, active version, drafts, counts, last run" }
  - { id: "I3", direction: "in", type: "request", description: "put_if_absent on locks/pipeline.json, stale after six hours" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/pipeline/run.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-004 Sweep orchestration

| Property | Value |
|---|---|
| ABB ID | ABB-004 |
| ABB Name | Sweep orchestration |
| Short Name | SWEEP |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Ingestion |
| Bounded context | BC-001 |
| Realises | CAP-002 |
| Realised by | SBB-002, SBB-013 |

One idempotent pass over every collection and stage, under a lock, repeated until a round changes nothing, started by uploads and backed by a schedule.

## 1  Purpose

The store stays current without an operator because every stage can be run again safely and one sweep runs at a time. Orchestration is what turns independent stages into a system that converges.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Stages in order.** ingest, provided ontology, refine, discover (when no version), extract, bind, candidates, project, load graph, load documents, load SPARQL, sync passages, status
- **Rounds.** Up to five, until nothing new is stored or discovered
- **Lock.** Conditional write with owner and TTL
- **Status.** Written at each stage and on failure

### 2.3  Attributes

- **Idempotence.** Each stage skips what is done, by marker files, pointers and hashes
- **Safety.** Only one sweep at a time; a stale lock is taken over
- **Observability.** The status page is the sweep's own report

### 2.4  Semantic

Inside: ordering, locking, rounds, status, the two triggers. Outside: what each stage does.

### 2.5  Identity & Access Management

The task role: the lake, Neptune write, the Knowledge Base ingestion job, the model. Started by EventBridge Pipes and Scheduler roles that may only run the task.

### 2.6  Observability

The ECS task log group; the status per collection; a dead-letter queue for uploads that could not start a task.

### 2.7  Governance & Policy Enforcement

Schedule and workers are inputs; the sweep is the only writer of Neptune and of gold.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | trigger | An upload event, a schedule, or a command |
| I2 | out | status | portal/status.json per collection: stage, active version, drafts, counts, last run |
| I3 | in | lock | put_if_absent on locks/pipeline.json, stale after six hours |

### 3.4  Capability dependencies (requires)

- ABB-002 (1): The lock and the status live in the lake
- ABB-006 (1): Publishes a provided ontology and auto-publishes a draft
- ABB-009 (1): Runs extraction
- ABB-011 (1): Runs projection and loading

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/pipeline/run.py; infra/modules/pipeline` |
| Capabilities | CAP-002 |
| Context | BC-001 |

## 5  Solution Building Block guidance

Realised as a Fargate task started by Pipes and Scheduler (SBB-002), or the CLI run command locally (SBB-013).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
