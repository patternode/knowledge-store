---
kind: capability
id: CAP-001
title: "CAP-001 Grounded knowledge from documents"
description: "The L1 capability: turning an organisation's documents into typed, cited facts and answering from them with nothing shown that was not checked."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
level: L1
parent: null
components:
  organisation: "The product owner holds the capability; a deployment's curator and administrator operate it"
  people: ["Product owner", "Curators (the ontology)", "Administrators (the deployment)", "Readers (the people who ask)"]
  processes:
    - "Ingest, refine, extract, project and load, as one idempotent sweep"
    - "Curate and publish ontology versions"
    - "Ask, check, show"
    - "Evaluate against a set"
  technology: "The pipeline image, the agent image, the portal and the stores, as one Terraform module"
maturity:
  current: 4
  target: 4
  assessment_date: 2026-10-16
  assessor: "Patternode (Dermot O'Brien), reversed from the implementation"
subdomain_kind: core
provided_by_platform: PL-001
realised_by_abbs: []
gaps:
  - "The split into deployable contexts is designed and not yet built (CN-006)"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# CAP-001 Grounded knowledge from documents

| Property | Value |
|---|---|
| Capability ID | CAP-001 |
| Level | L1 |
| Parent | none |
| Status | Draft, reversed from the implementation at 0.3.0 |
| Subdomain | core |
| Maturity | 4, target 4 |
| Realised by | none directly; its L2 capabilities are realised |

The L1 capability: turning an organisation's documents into typed, cited facts and answering from them with nothing shown that was not checked.

## 1  Purpose

Everything the store does serves one ability: to answer from what an organisation has written, in terms it owns, with every statement traceable. The L2 capabilities below are its parts; this one exists so the whole has a name and an owner.

## 2  Capability definition

| Dimension | For Knowledge Store |
|---|---|
| Organisation | The product owner holds the capability; a deployment's curator and administrator operate it |
| People | Product owner, Curators (the ontology), Administrators (the deployment), Readers (the people who ask) |
| Processes | Ingest, refine, extract, project and load, as one idempotent sweep; Curate and publish ontology versions; Ask, check, show; Evaluate against a set |
| Technology | The pipeline image, the agent image, the portal and the stores, as one Terraform module |

## 3  Sub-capabilities

The L2 capabilities CAP-002 to CAP-013 are its parts; see [the capability model](../README.md).

## 4  What the implementation does today

The whole of Knowledge Store as released: the pipeline, the ontology lifecycle, the graph, the agent and the portal, in service as the Patternode lab and as any deployment of the module.

## 5  Maturity

Current maturity is 4 on the 0 to 5 scale, read from the implementation: the capability is defined, built and in service in the Patternode lab and in any deployment of the module. Target 4.

## 6  Gaps

- The split into deployable contexts is designed and not yet built (CN-006)
