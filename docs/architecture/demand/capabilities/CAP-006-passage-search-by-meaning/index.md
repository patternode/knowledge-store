---
kind: capability
id: CAP-006
title: "CAP-006 Passage search by meaning"
description: "Finding the passage that answers a question that describes a situation rather than naming things, with one vector per passage so a hit is a passage id the graph's facts also cite."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
level: L2
parent: CAP-001
components:
  organisation: "The sweep syncs passages; the Knowledge Base ingests; the passage tools retrieve"
  people: ["Administrators (knowledge_base.enabled, embedding model)"]
  processes:
    - "Write each passage with its metadata to the lake's kb prefix and start an ingestion job when any changed"
    - "Retrieve by meaning, filtered to the collection and the caller's scope, then re-check"
    - "Fall back to keyword search over the index when the Knowledge Base is off"
  technology: "Bedrock Knowledge Base over S3 Vectors, Titan embeddings, chunking off, a tf-idf fallback"
maturity:
  current: 3
  target: 4
  assessment_date: 2026-10-16
  assessor: "Patternode (Dermot O'Brien), reversed from the implementation"
subdomain_kind: supporting
provided_by_platform: PL-001
realised_by_abbs: [ABB-004, ABB-012, ABB-013]
gaps:
  - "One embedding model, set at deployment; changing it rebuilds the index"
  - "No hybrid ranking across vector and keyword"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# CAP-006 Passage search by meaning

| Property | Value |
|---|---|
| Capability ID | CAP-006 |
| Level | L2 |
| Parent | CAP-001 |
| Status | Draft, reversed from the implementation at 0.3.0 |
| Subdomain | supporting |
| Maturity | 3, target 4 |
| Realised by | ABB-004, ABB-012, ABB-013 |

Finding the passage that answers a question that describes a situation rather than naming things, with one vector per passage so a hit is a passage id the graph's facts also cite.

## 1  Purpose

Frontline questions share no words with the article that answers them. A vector per passage, never a chunk of a chunk, finds it and lands on the same id the facts cite, so the two paths meet.

## 2  Capability definition

| Dimension | For Knowledge Store |
|---|---|
| Organisation | The sweep syncs passages; the Knowledge Base ingests; the passage tools retrieve |
| People | Administrators (knowledge_base.enabled, embedding model) |
| Processes | Write each passage with its metadata to the lake's kb prefix and start an ingestion job when any changed; Retrieve by meaning, filtered to the collection and the caller's scope, then re-check; Fall back to keyword search over the index when the Knowledge Base is off |
| Technology | Bedrock Knowledge Base over S3 Vectors, Titan embeddings, chunking off, a tf-idf fallback |

## 3  Sub-capabilities

| Sub-capability | What it covers | Status |
|---|---|---|
| Passage sync | Per-passage hash, deletions, one ingestion job per change | In place |
| Retrieval by meaning | Filtered retrieve, re-checked | In place |
| Keyword fallback | tf-idf over the index | In place |

## 4  What the implementation does today

kb/passages/<collection>/<passage id>.txt with a metadata sidecar, synced per passage hash; the Knowledge Base on S3 Vectors costs cents at rest; a passage tool Lambda outside the VPC calls Retrieve with the scope filter.

## 5  Maturity

Current maturity is 3 on the 0 to 5 scale, read from the implementation: the capability is defined, built and in service in the Patternode lab and in any deployment of the module. Target 4.

## 6  Gaps

- One embedding model, set at deployment; changing it rebuilds the index
- No hybrid ranking across vector and keyword
