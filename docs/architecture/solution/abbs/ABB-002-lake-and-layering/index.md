---
kind: abb
id: ABB-002
title: "ABB-002 Lake and layering"
short_name: "LAKE"
description: "The record of everything: one object store behind one port, with a stated key layout of layers and a collection prefix, so that every other store is a projection that can be rebuilt from it."
version: 0.2.0
status: draft
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Data"
part_of: BC-001
realises_capabilities: [CAP-002]
realised_by: [SBB-001]
requires: []
domains: [data]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "put, get, exists, list, put_if_absent, delete over keys" }
  - { id: "I2", direction: "out", type: "query", description: "The key layout every context reads: landing, bronze, silver, gold, ontology, config, kb, locks, usage" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/store.py, layout.py, collections.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-002 Lake and layering

| Property | Value |
|---|---|
| ABB ID | ABB-002 |
| ABB Name | Lake and layering |
| Short Name | LAKE |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Data |
| Bounded context | BC-001 |
| Realises | CAP-002 |
| Realised by | SBB-001 |

The record of everything: one object store behind one port, with a stated key layout of layers and a collection prefix, so that every other store is a projection that can be rebuilt from it.

## 1  Purpose

The design is a system of record plus projections. The lake is the record; its layers say what each object is (as uploaded, immutable, parsed, extracted), and the layout is a contract rather than a convention so a tool Lambda and the sweep agree without sharing code.

## 2  Building block

### 2.1  Component Diagram

The components below are what runs inside this one container, listed per the building block calibration standard: none of them is a building block of its own. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Store port.** A protocol with S3 and local filesystem adapters, and a prefix view per collection
- **Layout.** One module of key builders: bronze by content hash, silver by document id, gold by version and document, ontology by version, pointers, locks
- **Conditional write.** put_if_absent, used for the sweep's lock
- **Collections.** config/collections.json and a prefix per collection
- **Ledger.** usage/ledger/dt=<day>/ rows, one per model call, written by the callers' ledger client and read by the ledger report and the workbench's prices
- **Index.** The projection JSON per version under gold, loaded into one process by the tools when no graph store is configured

### 2.3  Attributes

- **Durability.** Versioned bucket, old versions kept thirty days, encrypted, TLS only
- **Portability.** The same layout on a local folder; the core needs no cloud SDK
- **Rebuildability.** Every projection is rebuilt from gold; nothing downstream is authoritative

### 2.4  Semantic

Inside: the bucket, its layout, the pointers, the lock and the ledger. Outside: everything that reads or writes it, and every store that is a projection of it.

### 2.5  Identity & Access Management

The pipeline task reads and writes the whole lake; the portal reads served prefixes and writes one; each tool Lambda reads the prefixes its toolset needs; the Knowledge Base role reads kb/. Grants are per prefix.

### 2.6  Observability

Bucket notifications feed the upload trigger; access is in CloudTrail; the sweep's status.json is the lake's own health page.

### 2.7  Governance & Policy Enforcement

Immutability by layer: bronze objects are never modified; gold per version is never rewritten; a version's files are checksummed in its manifest. Public access blocked; a force-destroy flag guards deletion.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | port | put, get, exists, list, put_if_absent, delete over keys |
| I2 | out | layout | The key layout every context reads: landing, bronze, silver, gold, ontology, config, kb, locks, usage |

### 3.4  Capability dependencies (requires)

None beyond the cross-cutting trio.

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/store.py, layout.py, collections.py, ledger.py; infra/modules/lake` |
| Capabilities | CAP-002 |
| Context | BC-001 |

## 5  Solution Building Block guidance

Realised as one S3 bucket (SBB-001). The folder form behind the same port is the command line's (SBB-015) and the test suite's, not a block of its own.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.2.0 | 2026-10-17 | Recalibrated to container grain: the ledger prefix and the projection index folded in as layout; SBB-013 retired |
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
