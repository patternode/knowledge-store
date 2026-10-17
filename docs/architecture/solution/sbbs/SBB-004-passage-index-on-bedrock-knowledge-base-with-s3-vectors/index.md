---
kind: sbb
id: SBB-004
title: "SBB-004 Passage index on Bedrock Knowledge Base with S3 Vectors"
description: "Search of passages by meaning at cents a month at rest, with the passage as the unit so a hit is a passage id."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-013]
realised_by_services: [pipeline, tools-passages]
products:
  - { name: "Amazon Bedrock Knowledge Bases", vendor: "AWS", licensing: "pay per use" }
  - { name: "Amazon S3 Vectors", vendor: "AWS", licensing: "storage and queries" }
  - { name: "Amazon Titan Text Embeddings v2", vendor: "AWS", licensing: "per token" }
product_mapping:
  - { abb_component: "Index", sbb_product: "A vector bucket with a passages index, 1,024 dimensions, cosine; chunking off so one passage is one vector" }
  - { abb_component: "Data source", sbb_product: "The lake's kb/passages prefix with metadata sidecars; an ingestion job per change" }
  - { abb_component: "Retrieve", sbb_product: "The passage tools Lambda calls Retrieve with collection and scope filters" }
cloud_provider: aws
deployment_model: managed
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-004 Passage index on Bedrock Knowledge Base with S3 Vectors

| Property | Value |
|---|---|
| SBB ID | SBB-004 |
| Realises | ABB-013 |
| Realised by services | pipeline, tools-passages |
| Products | Amazon Bedrock Knowledge Bases; Amazon S3 Vectors; Amazon Titan Text Embeddings v2 |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0, recalibrated to container grain |

Search of passages by meaning at cents a month at rest, with the passage as the unit so a hit is a passage id.

## 1  Purpose

An OpenSearch Serverless index costs hundreds a month idle; S3 Vectors costs cents. The decision is ADR-007.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Index | A vector bucket with a passages index, 1,024 dimensions, cosine; chunking off so one passage is one vector |
| Data source | The lake's kb/passages prefix with metadata sidecars; an ingestion job per change |
| Retrieve | The passage tools Lambda calls Retrieve with collection and scope filters |

## 3  Operation

knowledge_base.enabled false removes it; the keyword fallback serves searches; changing the embedding model rebuilds the index.

## 4  Cost

Cents at rest; embedding once per passage.

## 5  ABB traceability

ABB-013. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the reference architecture that composes this block with the others is RA-001.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain |
