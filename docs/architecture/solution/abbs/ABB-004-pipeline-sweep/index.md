---
kind: abb
id: ABB-004
title: "ABB-004 Pipeline sweep"
short_name: "SWEEP"
description: "The one deployable unit that keeps the store current: an idempotent pass over every collection, under a lock, started by uploads and backed by a schedule. Source adapters, refinement, ontology discovery and review, extraction, table binding, the candidate register, projection and loading, passage sync and the model client are its components, not blocks of their own."
version: 0.2.0
status: draft
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Pipeline"
part_of: BC-003
realises_capabilities: [CAP-002]
realised_by: [SBB-002]
requires:
  - { abb: ABB-002, cardinality: "1", rationale: "The lake it reads and writes, the lock and the status" }
  - { abb: ABB-006, cardinality: "0..1", rationale: "A version a curator published and activated; without one, the sweep discovers a draft or publishes a provided ontology with the same library" }
  - { abb: ABB-011, cardinality: "1", rationale: "Loads the graph store" }
  - { abb: ABB-013, cardinality: "0..1", rationale: "Syncs the passage index when it is enabled" }
domains: [application]
interfaces:
  - { id: "I1", direction: "in", type: "event", description: "An upload event, a schedule, or a command" }
  - { id: "I2", direction: "out", type: "event", description: "portal/status.json per collection: stage, active version, drafts, counts, last run" }
  - { id: "I3", direction: "in", type: "request", description: "put_if_absent on locks/pipeline.json, stale after six hours" }
  - { id: "I4", direction: "in", type: "stream", description: "Items and their bytes from each configured source" }
  - { id: "I5", direction: "out", type: "stream", description: "Bronze, silver, gold, drafts, candidates and the status written to the lake" }
  - { id: "I6", direction: "out", type: "stream", description: "Named graphs loaded into the knowledge graph store; passages synced into the passage index" }
  - { id: "I7", direction: "out", type: "request", description: "Model calls for discovery and extraction, priced into the ledger" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/pipeline/run.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-004 Pipeline sweep

| Property | Value |
|---|---|
| ABB ID | ABB-004 |
| ABB Name | Pipeline sweep |
| Short Name | SWEEP |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Pipeline |
| Bounded context | BC-003 |
| Realises | CAP-002 |
| Realised by | SBB-002 |

The one deployable unit that keeps the store current: an idempotent pass over every collection, under a lock, started by uploads and backed by a schedule. Source adapters, refinement, ontology discovery and review, extraction, table binding, the candidate register, projection and loading, passage sync and the model client are its components, not blocks of their own.

## 1  Purpose

The store stays current without an operator because every stage can be run again safely and one sweep runs at a time. Orchestration is what turns independent stages into a system that converges.

## 2  Building block

### 2.1  Component Diagram

The components below are what runs inside this one container, listed per the building block calibration standard: none of them is a building block of its own. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Orchestration.** Stages in order (ingest, provided ontology, refine, discover when no version, extract, bind, candidates, project, load graph, load documents, load SPARQL, sync passages, status); up to five rounds until nothing changes; the lock as a conditional write with owner and TTL; status at each stage and on failure; the two triggers
- **Source adapters.** One protocol, type, items() and fetch(item); built-in S3 landing, local directory and HTTPS adapters with public-address, redirect and size checks; a registry of built-ins then entry points
- **Refinement.** Parsers by extension then content type (text, markdown, HTML, JSON, PDF) with size caps; chunking at about 1,800 characters with content-derived ids and a chunker version; skip rules for unsupported, failed, empty and mapped files
- **Discovery and review.** A seeded round-robin sample; proposals per document; aggregation by normalised name with stability; one consolidation call; a review pass whose edits are applied in code; a Turtle writer with evidence comments and generated SHACL
- **Extraction.** A record_knowledge tool schema generated from the active version; the Converse loop with throttle retry, two repairs and salvage; shape, ontology, grounding and SHACL checks; content-derived IRIs and reified assertions as N-Quads; delta extraction of new terms only
- **Table binding.** File selection by path, suffix then name; rows as entities with content-derived IRIs; cells with canonical values; a binding record per logical table; re-bind when the hash, mapping or scope changed
- **Candidate register.** Terms extraction could not place and terms curators asked for, aggregated by kind and normalised term with documents, evidence and nearest existing term
- **Projection and loading.** Summary, ontology, entities, passages and documents as JSON per version; DROP and INSERT per named graph into the SPARQL store, skipping unchanged hashes; the optional graph and document backends; pointers that move only when counts check
- **Passage sync.** Per-passage hashes of text, scope and title; deletions; one ingestion job per change
- **Model client.** One Converse-shaped client over Bedrock or the Anthropic API by configuration, parameters a model rejects dropped per family, every call priced into the ledger

### 2.3  Attributes

- **Idempotence.** Each stage skips what is done, by marker files, pointers and hashes
- **Safety.** Only one sweep at a time; a stale lock is taken over
- **Observability.** The status page is the sweep's own report

### 2.4  Semantic

Inside: everything that runs in the sweep's process, from fetching bytes to moving a projection's pointer. Outside: the stores it reads and writes, the version a curator publishes, and the tools that query the result.

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
| I4 | in | data | Items and their bytes from each configured source |
| I5 | out | data | Bronze, silver, gold, drafts, candidates and the status written to the lake |
| I6 | out | data | Named graphs loaded into the knowledge graph store; passages synced into the passage index |
| I7 | out | request | Model calls for discovery and extraction, priced into the ledger |

### 3.4  Capability dependencies (requires)

- ABB-002 (1): The lake it reads and writes, the lock and the status
- ABB-006 (0..1): A version a curator published and activated; without one, the sweep discovers a draft or publishes a provided ontology with the same library
- ABB-011 (1): Loads the graph store
- ABB-013 (0..1): Syncs the passage index when it is enabled

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/pipeline/*.py; adapters/; refine/; ontology/discover.py, review.py, writer.py, candidates.py; extract/; structured/bind.py, values.py; graph/; llm.py, ledger.py; infra/modules/pipeline` |
| Capabilities | CAP-002 |
| Context | BC-003 |

## 5  Solution Building Block guidance

Realised as one image on one Fargate task with its triggers (SBB-002). Run on an operator's machine, the same stages are the command line's run command (SBB-015): the same image's entry point, not a second realisation of this block.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.2.0 | 2026-10-17 | Recalibrated to container grain: ABB-001, ABB-003, ABB-005, ABB-007, ABB-009, ABB-010 and the pipeline side of ABB-011, ABB-013 and ABB-022 folded in as components; renamed from Sweep orchestration |
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
