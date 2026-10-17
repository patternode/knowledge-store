---
kind: capability
id: CAP-002
title: "CAP-002 Document ingestion and passage derivation"
description: "Getting content in from configured sources, keeping one immutable content-addressed copy of each distinct file, and cutting it into deterministic passages, the unit a citation points at."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
level: L2
parent: CAP-001
components:
  organisation: "The administrator configures sources; the sweep runs without a person"
  people: ["Administrators (sources, uploads)", "Adapter authors (a source type of their own)"]
  processes:
    - "Configure sources per collection (type, options, scope)"
    - "Upload to landing or point at a source"
    - "Sweep: ingest to bronze, refine to silver, skip mapped tables"
    - "Add a source type through the adapter entry point"
  technology: "Source adapters behind one protocol, the lake with its layers, parsers by format, deterministic chunking"
maturity:
  current: 4
  target: 4
  assessment_date: 2026-10-16
  assessor: "Patternode (Dermot O'Brien), reversed from the implementation"
subdomain_kind: supporting
provided_by_platform: PL-001
realised_by_abbs: [ABB-024, ABB-002, ABB-028]
gaps:
  - "Only text-bearing formats are parsed (text, markdown, HTML, JSON, PDF); images and scans are skipped"
  - "The HTTP adapter fetches every run and relies on content addressing to deduplicate"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# CAP-002 Document ingestion and passage derivation

| Property | Value |
|---|---|
| Capability ID | CAP-002 |
| Level | L2 |
| Parent | CAP-001 |
| Status | Draft, reversed from the implementation at 0.3.0 |
| Subdomain | supporting |
| Maturity | 4, target 4 |
| Realised by | ABB-024, ABB-002, ABB-028 |

Getting content in from configured sources, keeping one immutable content-addressed copy of each distinct file, and cutting it into deterministic passages, the unit a citation points at.

## 1  Purpose

A citation is only as stable as the thing it points at. Ingestion keeps the bytes, records where they came from and their scope, and derives passages whose identifiers are a function of the content, so a fact extracted today still resolves after any number of sweeps.

## 2  Capability definition

| Dimension | For Knowledge Store |
|---|---|
| Organisation | The administrator configures sources; the sweep runs without a person |
| People | Administrators (sources, uploads), Adapter authors (a source type of their own) |
| Processes | Configure sources per collection (type, options, scope); Upload to landing or point at a source; Sweep: ingest to bronze, refine to silver, skip mapped tables; Add a source type through the adapter entry point |
| Technology | Source adapters behind one protocol, the lake with its layers, parsers by format, deterministic chunking |

## 3  Sub-capabilities

| Sub-capability | What it covers | Status |
|---|---|---|
| Source acquisition | Items and bytes from a configured source, through the adapter protocol | In place |
| Content addressing | One bronze copy per distinct file, with every source key that named it | In place |
| Parsing | Bytes to text and title, by extension then content type | In place |
| Passage derivation | Deterministic chunks with content-derived ids | In place |
| Sweep orchestration | Idempotent stages under one lock, started by uploads or a schedule | In place |

## 4  What the implementation does today

Three adapters (S3 landing, local directory, HTTPS URLs) and the entry point for more. Bronze is keyed by sha256; silver holds parsed text and passages of about 1,800 characters with ids derived from the document and the chunk. A mapped table is ingested but never refined. Sizes are capped at ingest (20 MB, PDFs 100 MB; HTTP 50 MB).

## 5  Maturity

Current maturity is 4 on the 0 to 5 scale, read from the implementation: the capability is defined, built and in service in the Patternode lab and in any deployment of the module. Target 4.

## 6  Gaps

- Only text-bearing formats are parsed (text, markdown, HTML, JSON, PDF); images and scans are skipped
- The HTTP adapter fetches every run and relies on content addressing to deduplicate
