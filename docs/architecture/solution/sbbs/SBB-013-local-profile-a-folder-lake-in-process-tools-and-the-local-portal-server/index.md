---
kind: sbb
id: SBB-013
title: "SBB-013 Local profile: a folder lake, in-process tools and the local portal server"
description: "The whole store on one machine over a folder, with no cloud, for development, evaluation and small corpora."
version: 0.1.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-002, ABB-004, ABB-012, ABB-014, ABB-019, ABB-021, ABB-023]
realised_by_services: [knowledge-store-cli, evaluation-runner]
products:
  - { name: "Python 3.12", vendor: "PSF", licensing: "PSF licence" }
  - { name: "rdflib, pySHACL, pypdf, PyYAML", vendor: "open source", licensing: "BSD and Apache" }
  - { name: "The Anthropic API or AWS credentials", vendor: "Anthropic or AWS", licensing: "per token" }
product_mapping:
  - { abb_component: "Lake", sbb_product: "LocalStore over a folder, the same layout" }
  - { abb_component: "Sweep", sbb_product: "knowledge-store run with the CLI; every stage a command" }
  - { abb_component: "Tools and agent", sbb_product: "LocalTools in process; answer_locally; a local rdflib SPARQL client" }
  - { abb_component: "Portal", sbb_product: "python -m knowledge_store.portal_api.local on loopback with a synthetic private caller and memory state" }
  - { abb_component: "Evaluation", sbb_product: "python -m knowledge_store.evals against the lake" }
cloud_provider: none
deployment_model: self-hosted
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-013 Local profile: a folder lake, in-process tools and the local portal server

| Property | Value |
|---|---|
| SBB ID | SBB-013 |
| Realises | ABB-002, ABB-004, ABB-012, ABB-014, ABB-019, ABB-021, ABB-023 |
| Realised by services | knowledge-store-cli, evaluation-runner |
| Products | Python 3.12; rdflib, pySHACL, pypdf, PyYAML; The Anthropic API or AWS credentials |
| Cloud | none, self-hosted |
| Status | active, as deployed at 0.3.0 |

The whole store on one machine over a folder, with no cloud, for development, evaluation and small corpora.

## 1  Purpose

The core depends on no cloud SDK; the ports have local adapters; it is how the test suite runs with a fake model.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Lake | LocalStore over a folder, the same layout |
| Sweep | knowledge-store run with the CLI; every stage a command |
| Tools and agent | LocalTools in process; answer_locally; a local rdflib SPARQL client |
| Portal | python -m knowledge_store.portal_api.local on loopback with a synthetic private caller and memory state |
| Evaluation | python -m knowledge_store.evals against the lake |

## 3  Operation

Install the package; set LAKE_URI and LLM_PROVIDER; run.

## 4  Cost

Model calls only.

## 5  ABB traceability

ABB-002, ABB-004, ABB-012, ABB-014, ABB-019, ABB-021, ABB-023. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the physical pattern that composes this block with the others is REF-001.
