---
kind: sbb
id: SBB-013
title: "SBB-013 Command line on Python, the local profile"
description: "The command line installed from the package on an operator's machine, running the whole store on a folder or against a deployment's bucket."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-028]
realised_by_services: [knowledge-store-cli]
products:
  - { name: "Python 3.12", vendor: "PSF", licensing: "PSF licence" }
  - { name: "rdflib, pySHACL, pypdf, PyYAML", vendor: "open source", licensing: "permissive" }
  - { name: "The Anthropic API or AWS credentials for Bedrock", vendor: "Anthropic or AWS", licensing: "per token" }
product_mapping:
  - { abb_component: "Pipeline in process", sbb_product: "The knowledge-store run command over a folder lake with the in-memory projection and in-process tools" }
  - { abb_component: "Ontology release", sbb_product: "knowledge-store ontology pull, diff, publish, activate; candidates --propose" }
  - { abb_component: "Ledger report", sbb_product: "knowledge-store ledger" }
  - { abb_component: "Local portal", sbb_product: "knowledge-store serve: the page and the API from the machine" }
cloud_provider: none
deployment_model: self-hosted
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-013 Command line on Python, the local profile

| Property | Value |
|---|---|
| SBB ID | SBB-013 |
| Realises | ABB-028 |
| Realised by services | knowledge-store-cli |
| Products | Python 3.12; rdflib, pySHACL, pypdf, PyYAML; The Anthropic API or AWS credentials for Bedrock |
| Cloud | none, self-hosted |
| Status | active, as deployed at 0.3.0, recalibrated to container grain |

The command line installed from the package on an operator's machine, running the whole store on a folder or against a deployment's bucket.

## 1  Purpose

One machine and one model provider are enough to run, evaluate and curate; the same code runs here and in the deployment, so no path exists only locally.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Pipeline in process | The knowledge-store run command over a folder lake with the in-memory projection and in-process tools |
| Ontology release | knowledge-store ontology pull, diff, publish, activate; candidates --propose |
| Ledger report | knowledge-store ledger |
| Local portal | knowledge-store serve: the page and the API from the machine |

## 3  Operation

pip install; credentials for one provider; point at a folder or a bucket.

## 4  Cost

The operator's model calls.

## 5  ABB traceability

ABB-028. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the reference architecture that composes this block with the others is RA-001.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain |
