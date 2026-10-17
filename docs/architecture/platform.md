---
kind: platform
id: PL-001
title: "PL-001 Knowledge Store"
short_name: "KS"
description: "A knowledge store that turns an organisation's documents into an ontology-typed knowledge graph and answers questions from it with every statement linked to its source, deployed as one stack in the organisation's own account."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
strategic_owner: "Product owner, Knowledge Store"
lifecycle_state: baseline
classification: public
owns_outcomes: [OC-001, OC-002, OC-003]
provides_capabilities: [CAP-001, CAP-002, CAP-003, CAP-004, CAP-005, CAP-006, CAP-007, CAP-008, CAP-009, CAP-010, CAP-011, CAP-012, CAP-013]
contains_bounded_contexts: [BC-001, BC-002, BC-003, BC-004, BC-005, BC-006, BC-007, BC-008]
self_service_interfaces:
  - "The Terraform module infra/modules/knowledge-store, pinned by release tag (CT-010)"
  - "The chat page and its HTTP API (CT-001)"
  - "The agent's tools over MCP through AgentCore Gateway (CT-002, CT-003)"
  - "The CLI knowledge-store (CT-014)"
  - "The published ontology renditions per version (CT-006)"
consuming_teams: ["Patternode: the Knowledge Store lab in patternode-platform", "Any organisation deploying the module in its own AWS account"]
slos:
  - { name: "Idle cost", target: "close to nothing while no question is asked and no sweep runs, apart from the graph instance" }
  - { name: "Shown statements grounded", target: "100 percent: a claim is shown only after its citations pass the checks" }
tier: solo
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# PL-001 Knowledge Store

| Property | Value |
|---|---|
| Platform ID | PL-001 |
| Name | Knowledge Store |
| Strategic owner | Product owner, Knowledge Store |
| Owner team | Patternode (Dermot O'Brien) |
| Status | Draft |

## Purpose

Knowledge Store takes a corpus of documents, applies an ontology to it (one the organisation brings, or one discovered from the documents and reviewed by a person), extracts facts against that ontology into a knowledge graph in which every fact cites the passage it came from, and answers questions from the graph through an agent whose every shown statement is linked to a passage or a table cell the reader may read. It is a platform in the continuum's sense: one team owns it, it is consumed through stated interfaces, and a deployment is self-service from one Terraform module in the consumer's own account. This page is the top of the catalogue; [landscape.md](landscape.md) says what it consumes and who consumes it.

## Outcomes it owns

| Outcome | What it is |
|---|---|
| OC-001 Answers a reader can check | No statement is shown without a source the reader may open |
| OC-002 An ontology the organisation owns | The ontology is curated by people, versioned, and grown from what extraction found it lacked |
| OC-003 A store the organisation runs itself, at a cost it can see | One stack in its own account, no data leaving it, idle cost near zero, spend valves |

## Capabilities it provides

The capability model is [demand/capabilities/README.md](demand/capabilities/README.md). CAP-001 is the L1 capability, grounded knowledge from documents; CAP-002 to CAP-013 are its L2 capabilities, each provided by this platform.

## Bounded contexts it contains

| Context | Model | Subdomain |
|---|---|---|
| BC-001 Ingestion | Sources, documents, passages and the lake's layers | supporting |
| BC-002 Ontology | Terms, versions, renditions, drafts and candidates | core |
| BC-003 Extraction | Extraction runs, assertions, SHACL, table snapshots and cells | core |
| BC-004 Knowledge graph | The record per document, projections, fixed queries | core |
| BC-005 Answering | Questions, claims, citations, checks, valves, steps | core |
| BC-006 Portal and identity | People, sessions, scope, quotas, the chat page | supporting |
| BC-007 Evaluation | Evaluation sets, runs, scores | supporting |
| BC-008 Platform services | Model access, the cost ledger, configuration, deployment | generic |

The split is the one the code suggests, not yet the one it is deployed as: the pipeline image composes BC-001 to BC-004 in one process, and the agent image composes BC-004 tools and BC-005. The services register says which contexts each deployable composes today; CN-006 holds the decoupling question.

## Self-service interfaces and consumers

A consumer deploys the module into its own account with its own inputs (collections, models, network, valves), loads documents by uploading them, and reaches the store through the chat page, the HTTP API, the MCP tools and the CLI. Patternode's own deployment is the Knowledge Store lab in patternode-platform, which pins a release tag of the module; its product page there is `pna:PRD-003`.

## Measures

The outcomes carry the measures. The platform's own commitments are the two in the front matter: idle cost close to nothing, and no shown statement without a passed check.
