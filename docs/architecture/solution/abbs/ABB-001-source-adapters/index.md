---
kind: abb
id: ABB-001
title: "ABB-001 Source adapters"
short_name: "SRC"
description: "Acquisition of content from a configured source, behind one protocol: items and their bytes, nothing more. Parsing belongs to refinement; skipping and content addressing to ingestion."
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
  - { abb: ABB-002, cardinality: "1", rationale: "Every fetched item is written to the lake through its port" }
domains: [application, data]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "A source: type, options, scope" }
  - { id: "I2", direction: "out", type: "query", description: "Items and their bytes, with version, name, uri, content type and metadata" }
  - { id: "I3", direction: "in", type: "request", description: "An adapter registered under the knowledge_store.adapters entry point" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/adapters/base.py, __init__.py, s3_landing.py, local_dir.py, http_urls.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-001 Source adapters

| Property | Value |
|---|---|
| ABB ID | ABB-001 |
| ABB Name | Source adapters |
| Short Name | SRC |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Ingestion |
| Bounded context | BC-001 |
| Realises | CAP-002 |
| Realised by | SBB-014 |

Acquisition of content from a configured source, behind one protocol: items and their bytes, nothing more. Parsing belongs to refinement; skipping and content addressing to ingestion.

## 1  Purpose

Sources differ (an upload prefix, a folder, a list of URLs, a system of record); what the store needs from each is the same: what is there, and the bytes of one thing. Keeping that behind a protocol lets a deployment add a source type without touching the pipeline.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Adapter protocol.** type, items(), fetch(item); a value object per item
- **Built-in adapters.** S3 landing (the default, per collection), local directory, HTTPS URLs with public-address and redirect checks
- **Registry.** Built-ins first, then entry points, chosen by the source's type

### 2.3  Attributes

- **Extensibility.** A new source is a package with one class and one entry point
- **Safety.** The HTTP adapter refuses non-HTTPS, private addresses and oversized bodies, on redirects too

### 2.4  Semantic

Inside: listing and fetching from a source, and the version an adapter uses to skip unchanged items. Outside: deciding whether to keep an item (ingestion), what its text is (refinement), and anything a source's own permissions say (CN-002).

### 2.5  Identity & Access Management

The adapter runs with the pipeline task's role; a source in another bucket needs a read grant on it. Credentials for a live source would be the adapter's to hold, from the secret store, never in configuration.

### 2.6  Observability

Per-source counts of items seen, fetched and skipped in the sweep's log and status.

### 2.7  Governance & Policy Enforcement

Sources are deployment inputs; a change is an apply. Document content is untrusted: nothing an adapter fetches is executed or trusted beyond its bytes.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | config | A source: type, options, scope |
| I2 | out | data | Items and their bytes, with version, name, uri, content type and metadata |
| I3 | in | registry | An adapter registered under the knowledge_store.adapters entry point |

### 3.4  Capability dependencies (requires)

- ABB-002 (1): Every fetched item is written to the lake through its port

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/adapters/base.py, __init__.py, s3_landing.py, local_dir.py, http_urls.py` |
| Capabilities | CAP-002 |
| Context | BC-001 |

## 5  Solution Building Block guidance

Realised in the pipeline image. A live source (CN-003) is an adapter plus a mapping, not a new path.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
