---
kind: sbb
id: SBB-015
title: "SBB-015 Command line on an operator's machine"
description: "The knowledge-store package installed on an operator's machine: one deployable unit with two entry points, the knowledge-store command for the ontology lifecycle and the local run of the sweep, and python -m knowledge_store.evals for evaluation, over a lake in S3 or a folder."
version: 0.1.0
status: active
created: 2026-10-17
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-006, ABB-021]
realised_by_services: [knowledge-store-cli, evaluation-runner]
products:
  - { name: "Python 3.12", vendor: "PSF", licensing: "PSF licence" }
  - { name: "The knowledge-store package: rdflib, pySHACL, pypdf, PyYAML, boto3", vendor: "open source", licensing: "BSD, Apache-2.0 and MIT" }
  - { name: "AWS credentials or the Anthropic API", vendor: "AWS or Anthropic", licensing: "per use" }
product_mapping:
  - { abb_component: "Ontology commands", sbb_product: "pull, diff, publish, activate, render, candidates --propose and the mapping checks, against the lake in S3 with the curator's AWS principal" }
  - { abb_component: "Evaluation", sbb_product: "python -m knowledge_store.evals against a lake in process or against the deployed chat with a person's token; reports under build/eval/" }
  - { abb_component: "Local run", sbb_product: "knowledge-store run over a folder lake (LAKE_URI), the same stages as the sweep, for development and the test suite with a fake model" }
  - { abb_component: "Local server", sbb_product: "python -m knowledge_store.portal_api.local: the chat API handler on loopback with a synthetic private caller and memory state, serving the chat page files" }
  - { abb_component: "Ledger report", sbb_product: "knowledge-store ledger report over usage/ledger/" }
cloud_provider: none
deployment_model: self-hosted
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-015 Command line on an operator's machine

| Property | Value |
|---|---|
| SBB ID | SBB-015 |
| Realises | ABB-006, ABB-021 |
| Realised by services | knowledge-store-cli, evaluation-runner |
| Products | Python 3.12; The knowledge-store package: rdflib, pySHACL, pypdf, PyYAML, boto3; AWS credentials or the Anthropic API |
| Cloud | none, self-hosted |
| Status | active, as deployed at 0.3.0; added in the recalibration of 2026-10-17 |

The knowledge-store package installed on an operator's machine: one deployable unit with two entry points, the knowledge-store command for the ontology lifecycle and the local run of the sweep, and python -m knowledge_store.evals for evaluation, over a lake in S3 or a folder.

## 1  Purpose

A curator and an evaluator work from their own machine with their own credentials; the package is the same code the images carry, so what runs locally is what runs in the account. One install is one deployable unit, which is why its two commands share one block.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Ontology commands | pull, diff, publish, activate, render, candidates --propose and the mapping checks, against the lake in S3 with the curator's AWS principal |
| Evaluation | python -m knowledge_store.evals against a lake in process or against the deployed chat with a person's token; reports under build/eval/ |
| Local run | knowledge-store run over a folder lake (LAKE_URI), the same stages as the sweep, for development and the test suite with a fake model |
| Local server | python -m knowledge_store.portal_api.local: the chat API handler on loopback with a synthetic private caller and memory state, serving the chat page files |
| Ledger report | knowledge-store ledger report over usage/ledger/ |

## 3  Operation

pip install the package at a release tag; set LAKE_URI and LLM_PROVIDER; run. The local run and the local server replace the deployed sweep and API on one machine for development, and are not a deployment of their own.

## 4  Cost

The operator's machine, and model calls when a command makes them.

## 5  ABB traceability

ABB-006, ABB-021. The command line container that realises the ontology publisher and the evaluation runner; the local run of the sweep is ABB-004's image entry point and the local server is ABB-019's handler, not realisations of their own. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the physical pattern that composes this block with the others is REF-001.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-17 | Added in the recalibration to container grain |
