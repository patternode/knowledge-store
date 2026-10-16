---
kind: abb
id: ABB-003
title: "ABB-003 Document refinement"
short_name: "REFINE"
description: "Bytes to text and title by format, then deterministic passages: the step that makes a document citable."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Ingestion"
part_of: BC-001
realises_capabilities: [CAP-002]
realised_by: [SBB-014]
requires:
  - { abb: ABB-002, cardinality: "1", rationale: "Reads bronze, writes silver" }
domains: [application, data]
interfaces:
  - { id: "I1", direction: "in", type: "query", description: "A bronze object and its meta" }
  - { id: "I2", direction: "out", type: "query", description: "A silver document (text, title) and its passages, or a skipped record with its reason" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/refine/parsers.py, html_text.py, chunk.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-003 Document refinement

| Property | Value |
|---|---|
| ABB ID | ABB-003 |
| ABB Name | Document refinement |
| Short Name | REFINE |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Ingestion |
| Bounded context | BC-001 |
| Realises | CAP-002 |
| Realised by | SBB-014 |

Bytes to text and title by format, then deterministic passages: the step that makes a document citable.

## 1  Purpose

A citation is a passage id and a quote. The id has to be the same tomorrow and the quote has to be found by the check, so chunking is deterministic and content-derived and parsing is a pure function of the bytes.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Parsers.** By extension then content type: text, markdown, HTML (table rows kept on one line), JSON (flattened), PDF; size caps
- **Chunking.** About 1,800 characters, at most 3,000, with an id from the document id, the sequence and the chunk hash; a chunker version string
- **Skip rules.** Unsupported, failed, empty, or mapped (a table the mapping names is not prose)

### 2.3  Attributes

- **Determinism.** Same bytes, same passages, same ids, across sweeps and machines
- **Idempotence.** The silver document is written last and is the marker; reparse is explicit

### 2.4  Semantic

Inside: parsing and chunking. Outside: what a passage means (extraction), how it is searched (the passage index).

### 2.5  Identity & Access Management

The pipeline task's role; no secrets.

### 2.6  Observability

Counts of refined and skipped documents by reason in the status.

### 2.7  Governance & Policy Enforcement

Formats are code; a new parser is a pull request. Document text is untrusted and is never evaluated.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | data | A bronze object and its meta |
| I2 | out | data | A silver document (text, title) and its passages, or a skipped record with its reason |

### 3.4  Capability dependencies (requires)

- ABB-002 (1): Reads bronze, writes silver

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/refine/parsers.py, html_text.py, chunk.py; pipeline/refine.py` |
| Capabilities | CAP-002 |
| Context | BC-001 |

## 5  Solution Building Block guidance

Realised in the pipeline image; a format needing OCR or layout analysis would be a new parser behind the same registry.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
