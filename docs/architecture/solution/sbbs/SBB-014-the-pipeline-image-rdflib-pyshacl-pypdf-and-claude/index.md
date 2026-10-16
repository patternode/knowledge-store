---
kind: sbb
id: SBB-014
title: "SBB-014 The pipeline image: rdflib, pySHACL, pypdf and Claude"
description: "The one container that holds BC-001 to BC-004's pipeline side, built from the repository and run as the sweep."
version: 0.1.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-001, ABB-003, ABB-005, ABB-006, ABB-007, ABB-008, ABB-009, ABB-010, ABB-011]
realised_by_services: [pipeline]
products:
  - { name: "rdflib", vendor: "RDFLib", licensing: "BSD" }
  - { name: "pySHACL", vendor: "RDFLib", licensing: "Apache-2.0" }
  - { name: "pypdf", vendor: "pypdf", licensing: "BSD" }
  - { name: "PyYAML", vendor: "PyYAML", licensing: "MIT" }
  - { name: "boto3", vendor: "AWS", licensing: "Apache-2.0" }
  - { name: "Claude through the model client", vendor: "Anthropic", licensing: "per token" }
product_mapping:
  - { abb_component: "Adapters and refinement", sbb_product: "The built-in adapters, the parsers, the chunker" }
  - { abb_component: "Ontology", sbb_product: "rdflib for the master and renditions; the discovery and review calls" }
  - { abb_component: "Extraction", sbb_product: "The tool schema, the extractor, pySHACL validation, N-Quads" }
  - { abb_component: "Binding and projection", sbb_product: "Snapshots, the index JSON, the loaders" }
cloud_provider: aws
deployment_model: self-hosted
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-014 The pipeline image: rdflib, pySHACL, pypdf and Claude

| Property | Value |
|---|---|
| SBB ID | SBB-014 |
| Realises | ABB-001, ABB-003, ABB-005, ABB-006, ABB-007, ABB-008, ABB-009, ABB-010, ABB-011 |
| Realised by services | pipeline |
| Products | rdflib; pySHACL; pypdf; PyYAML; boto3; Claude through the model client |
| Cloud | aws, self-hosted |
| Status | active, as deployed at 0.3.0 |

The one container that holds BC-001 to BC-004's pipeline side, built from the repository and run as the sweep.

## 1  Purpose

One image because the stages share the lake port, the ontology model and the model client; the split into contexts is CN-006.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Adapters and refinement | The built-in adapters, the parsers, the chunker |
| Ontology | rdflib for the master and renditions; the discovery and review calls |
| Extraction | The tool schema, the extractor, pySHACL validation, N-Quads |
| Binding and projection | Snapshots, the index JSON, the loaders |

## 3  Operation

Built by SBB-009; the task uses :latest; extras aws plus the chosen backends.

## 4  Cost

In SBB-002.

## 5  ABB traceability

ABB-001, ABB-003, ABB-005, ABB-006, ABB-007, ABB-008, ABB-009, ABB-010, ABB-011. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the physical pattern that composes this block with the others is REF-001.
