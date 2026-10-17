---
kind: abb
id: ABB-010
title: "ABB-010 Table binding"
short_name: "BIND"
description: "Copying a mapped table at its content hash into gold as rows that are entities, values that are cells, and assertions that cite the cells, validated by SHACL, keeping old snapshots so citations resolve."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Extraction"
part_of: BC-003
realises_capabilities: [CAP-004, CAP-007]
realised_by: [SBB-014]
requires:
  - { abb: ABB-008, cardinality: "1", rationale: "The published mapping" }
  - { abb: ABB-002, cardinality: "1", rationale: "Bronze objects and gold" }
domains: [data]
interfaces:
  - { id: "I1", direction: "in", type: "query", description: "The structured mapping rendition; the bronze file the mapping names" }
  - { id: "I2", direction: "out", type: "query", description: "gold/<v>/structured/<source>/<snapshot>.nq and .jsonl; binding.json" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/structured/bind.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-010 Table binding

| Property | Value |
|---|---|
| ABB ID | ABB-010 |
| ABB Name | Table binding |
| Short Name | BIND |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Extraction |
| Bounded context | BC-003 |
| Realises | CAP-004, CAP-007 |
| Realised by | SBB-014 |

Copying a mapped table at its content hash into gold as rows that are entities, values that are cells, and assertions that cite the cells, validated by SHACL, keeping old snapshots so citations resolve.

## 1  Purpose

A table fact is cited by cell, and a figure is recomputed from the snapshot it was computed over. Binding makes the snapshot a first-class part of the record rather than a cache.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **File selection.** Exact path, suffix, then name; ties refused; size and row caps
- **Row to entity.** Class plus key columns as the IRI; relations joined within the snapshot; a miss recorded
- **Cells.** Column, canonical value, raw text, snapshot, row key, scope
- **Binding record.** Per logical table: source, snapshot, mapping hash, scope, counts
- **Re-bind rule.** When the hash, the mapping hash or the scope changed

### 2.3  Attributes

- **Determinism.** No model call; same file, same graph
- **Stability.** Old snapshots are kept; a citation names its snapshot

### 2.4  Semantic

Inside: the snapshot. Outside: querying it (ABB-012) and citing it (ABB-015).

### 2.5  Identity & Access Management

The pipeline task; a private table's cells carry the scope.

### 2.6  Observability

The binding record and the bind report of misses.

### 2.7  Governance & Policy Enforcement

A snapshot that fails SHACL is not activated; the previous one stays readable.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | artefact | The structured mapping rendition; the bronze file the mapping names |
| I2 | out | data | gold/<v>/structured/<source>/<snapshot>.nq and .jsonl; binding.json |

### 3.4  Capability dependencies (requires)

- ABB-008 (1): The published mapping
- ABB-002 (1): Bronze objects and gold

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/structured/bind.py; values.py` |
| Capabilities | CAP-004, CAP-007 |
| Context | BC-003 |

## 5  Solution Building Block guidance

Realised in the pipeline image.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
