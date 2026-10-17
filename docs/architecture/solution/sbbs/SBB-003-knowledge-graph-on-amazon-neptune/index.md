---
kind: sbb
id: SBB-003
title: "SBB-003 Knowledge graph on Amazon Neptune"
description: "The gold RDF as it is, in a SPARQL store the graph tools query read-only, in private subnets."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-011]
realised_by_services: [pipeline, tools-graph]
products:
  - { name: "Amazon Neptune Database", vendor: "AWS", licensing: "instance hours, or Serverless NCUs" }
product_mapping:
  - { abb_component: "Named graphs", sbb_product: "One per document per version plus the T-Box, loaded by DROP and INSERT per graph with per-graph hashes" }
  - { abb_component: "Query", sbb_product: "SPARQL over HTTPS with SigV4; fixed queries from the ontology" }
  - { abb_component: "Placement", sbb_product: "Private subnets, IAM authentication, port 8182 open to the graph tools and the pipeline only" }
cloud_provider: aws
deployment_model: managed
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-003 Knowledge graph on Amazon Neptune

| Property | Value |
|---|---|
| SBB ID | SBB-003 |
| Realises | ABB-011 |
| Realised by services | pipeline, tools-graph |
| Products | Amazon Neptune Database |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0, recalibrated to container grain |

The gold RDF as it is, in a SPARQL store the graph tools query read-only, in private subnets.

## 1  Purpose

The record is RDF; a store that speaks it directly needs no second model. Neptune is managed, IAM-authenticated and private. CN-001 weighs it against Neo4j for larger graphs.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Named graphs | One per document per version plus the T-Box, loaded by DROP and INSERT per graph with per-graph hashes |
| Query | SPARQL over HTTPS with SigV4; fixed queries from the ontology |
| Placement | Private subnets, IAM authentication, port 8182 open to the graph tools and the pipeline only |

## 3  Operation

db.t3.medium by default or Serverless; knowledge_graph.enabled false removes it and the tools answer from memory; a query timeout of thirty seconds.

## 4  Cost

About sixty dollars a month for the instance; the one fixed cost of a deployment.

## 5  ABB traceability

ABB-011. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the reference architecture that composes this block with the others is RA-001.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain |
