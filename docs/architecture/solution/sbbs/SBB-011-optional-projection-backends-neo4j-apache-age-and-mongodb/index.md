---
kind: sbb
id: SBB-011
title: "SBB-011 Optional projection backends: Neo4j, Apache AGE and MongoDB"
description: "Backends for a collection that has outgrown one process's memory, each behind the same port and filled by the sweep, none required."
version: 0.1.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-011]
realised_by_services: [pipeline, portal-api]
products:
  - { name: "Neo4j or AuraDB", vendor: "Neo4j", licensing: "instance" }
  - { name: "PostgreSQL with Apache AGE", vendor: "PostgreSQL and Apache", licensing: "server" }
  - { name: "MongoDB or a wire-compatible service", vendor: "MongoDB", licensing: "instance" }
product_mapping:
  - { abb_component: "Graph backend", sbb_product: "GRAPH_BACKEND neo4j or age: a graph per load keyed by collection, version and build, filled by the load stage; traversals run on the backend's two primitives" }
  - { abb_component: "Document projection", sbb_product: "PROJECTION_STORE mongodb: entities, passages and documents with multikey indexes; the portal holds nothing in memory" }
  - { abb_component: "Chat state", sbb_product: "CHAT_STATE mongodb as an alternative to DynamoDB" }
cloud_provider: multi
deployment_model: hybrid
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-011 Optional projection backends: Neo4j, Apache AGE and MongoDB

| Property | Value |
|---|---|
| SBB ID | SBB-011 |
| Realises | ABB-011 |
| Realised by services | pipeline, portal-api |
| Products | Neo4j or AuraDB; PostgreSQL with Apache AGE; MongoDB or a wire-compatible service |
| Cloud | multi, hybrid |
| Status | active, as deployed at 0.3.0 |

Backends for a collection that has outgrown one process's memory, each behind the same port and filled by the sweep, none required.

## 1  Purpose

Memory is the default because every backend has a monthly floor (ADR-008); the ports exist so the switch is configuration.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Graph backend | GRAPH_BACKEND neo4j or age: a graph per load keyed by collection, version and build, filled by the load stage; traversals run on the backend's two primitives |
| Document projection | PROJECTION_STORE mongodb: entities, passages and documents with multikey indexes; the portal holds nothing in memory |
| Chat state | CHAT_STATE mongodb as an alternative to DynamoDB |

## 3  Operation

A load goes to a new graph and the pointer moves only when counts check; the previous load is kept for rollback; contract tests run the suites against emulators.

## 4  Cost

A monthly floor per backend.

## 5  ABB traceability

ABB-011. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the physical pattern that composes this block with the others is REF-001.
