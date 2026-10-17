---
kind: abb
id: ABB-002
title: "ABB-002 Lake"
short_name: "LAKE"
description: "The record of everything: one object store behind one port, with a stated layout of layers, the ontology versions, the candidate register and the ledger, so that every other store is a projection that can be rebuilt from it."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Data"
part_of: BC-001
realises_capabilities: [CAP-002, CAP-003]
realised_by: [SBB-001]
requires: []
domains: [data]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "put, get, exists, list, put_if_absent, delete over keys (the store port)" }
  - { id: "I2", direction: "out", type: "query", description: "The key layout every container reads: landing, bronze, silver, gold, ontology, config, kb, locks, usage (CT-015)" }
  - { id: "I3", direction: "out", type: "event", description: "An object created under landing/ or at ontology/active.json (CT-005)" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/store.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-002 Lake

| Property | Value |
|---|---|
| ABB ID | ABB-002 |
| ABB Name | Lake |
| Short Name | LAKE |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0, recalibrated to container grain |
| Category | Data |
| Bounded context | BC-001 |
| Realises | CAP-002, CAP-003 |
| Realised by | SBB-001 |
| Grain | One C4 container: passes the container test of the [calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md) |

The record of everything: one object store behind one port, with a stated layout of layers, the ontology versions, the candidate register and the ledger, so that every other store is a projection that can be rebuilt from it.

## 1  Purpose

The design is a system of record plus projections. The lake is the record; its layers say what each object is (as uploaded, immutable, parsed, extracted, published), and the layout is a contract rather than a convention, so a tool Lambda can read a prefix without the parser that wrote it. One bucket is one container; its zones are rows below, as the calibration standard requires.

## 2  Building block

### 2.1  Component Diagram

The components below are the boxes of this container's component diagram, which is not yet drawn. The outside view of this block is its box in [AP-001](../../patterns/AP-001-ontology-driven-graphrag/index.md) and the row of its SBB in [RA-001](../../patterns/RA-001-knowledge-store-on-aws/index.md).

### 2.2  Components

- **Store port.** A protocol with S3 and local filesystem adapters, and a prefix view per collection
- **Layout.** One module of key builders: bronze by content hash, silver by document id, gold by version, ontology by version, kb, locks, config and usage
- **Layers.** landing (as uploaded, never modified by code), bronze (immutable, one copy per distinct file), silver (parsed text and passages), gold (facts, extractions, candidates, structured snapshots and the index, per version)
- **Ontology versions.** ontology/versions/<v> with the master, the shapes, the manifest with checksums and every rendition; drafts, the candidate register, requests and the active pointer (ST-005, CT-006)
- **Lock and status.** locks/pipeline.json with a TTL and conditional writes; portal/status.json per collection
- **Ledger.** usage/ledger/dt=<day>/ with one row per model call (ST-016)
- **Conditional write.** put_if_absent for the lock and bronze/_seen
- **Collections.** config/collections.json and collections/<id>/config, written by Terraform, read by everything

### 2.3  Attributes

- **Durability.** Versioned bucket, old versions kept thirty days, encrypted, TLS only
- **Portability.** The same layout on a local folder; the core needs no cloud SDK
- **Rebuildability.** Every projection is derived from gold and the ontology version it names
- **Immutability by layer.** Bronze objects and published versions are never rewritten

### 2.4  Semantic

Inside: the port, the layout, the layers and what each holds. Outside: the code that writes a layer, which is the pipeline (ABB-024) for bronze, silver, gold and the candidate register, the command line (ABB-028) for a published version, and Terraform for configuration.

### 2.5  Identity & Access Management

The pipeline task reads and writes the whole lake; the Chat API reads served prefixes and writes requests; each tool Lambda reads the prefixes its toolset needs; the Knowledge Base role reads kb/. Grants are per prefix.

### 2.6  Observability

Bucket notifications feed the upload trigger; access is in CloudTrail; the status page per collection is the lake's own health page.

### 2.7  Governance & Policy Enforcement

Bronze objects are never modified; gold per version is never rewritten; a version's files are checksummed in its manifest and a published version is immutable (ADR-005). Public access blocked; a force-destroy flag guards deletion.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | request | put, get, exists, list, put_if_absent, delete over keys (the store port) |
| I2 | out | query | The key layout every container reads: landing, bronze, silver, gold, ontology, config, kb, locks, usage (CT-015) |
| I3 | out | event | An object created under landing/ or at ontology/active.json (CT-005) |

### 3.4  Capability dependencies (requires)

None beyond the cross-cutting trio.

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/store.py, layout.py, collections.py, ontology/versions.py (the layout of a version); infra/modules/lake` |
| Capabilities | CAP-002, CAP-003 |
| Context | BC-001 |

## 5  Solution Building Block guidance

Realised as one S3 bucket (SBB-001). On an operator's machine the same layout is a folder, which the command line (ABB-028, SBB-013) uses in place of the bucket.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain |
