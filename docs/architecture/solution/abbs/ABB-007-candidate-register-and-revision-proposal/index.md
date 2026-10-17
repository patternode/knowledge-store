---
kind: abb
id: ABB-007
title: "ABB-007 Candidate register and revision proposal"
short_name: "CAND"
description: "The terms extraction could not place and the terms curators asked for, aggregated with their evidence and nearest existing term, and proposed as the next minor version with the current ontology held fixed."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Ontology"
part_of: BC-002
realises_capabilities: [CAP-003, CAP-012]
realised_by: [SBB-014, SBB-012]
requires:
  - { abb: ABB-009, cardinality: "1", rationale: "Candidates come from extraction" }
  - { abb: ABB-017, cardinality: "0..1", rationale: "Requests come from the workbench" }
  - { abb: ABB-006, cardinality: "1", rationale: "A proposal is a draft for publish" }
domains: [application, business]
interfaces:
  - { id: "I1", direction: "in", type: "query", description: "gold/<v>/candidates per document; ontology/requests" }
  - { id: "I2", direction: "out", type: "query", description: "ontology/candidates/register.json; a revision draft one minor version up" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/ontology/candidates.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-007 Candidate register and revision proposal

| Property | Value |
|---|---|
| ABB ID | ABB-007 |
| ABB Name | Candidate register and revision proposal |
| Short Name | CAND |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Ontology |
| Bounded context | BC-002 |
| Realises | CAP-003, CAP-012 |
| Realised by | SBB-014, SBB-012 |

The terms extraction could not place and the terms curators asked for, aggregated with their evidence and nearest existing term, and proposed as the next minor version with the current ontology held fixed.

## 1  Purpose

Growth from demand, through a person. The register makes the demand visible; the proposal makes it a draft; nothing enters the ontology until published.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Register.** By kind and normalised term: documents, evidence, nearest, covered_by from synonyms, asked and questions from requests
- **Proposal.** Terms with two or more documents or a request, not covered; consolidated with the prior version; a warning when the result would change an existing term

### 2.3  Attributes

- **Evidence.** A candidate is kept only when its evidence is verbatim in a cited passage
- **Restraint.** A proposal is additive by construction and says when it is not

### 2.4  Semantic

Inside: the register and the proposal. Outside: review and publish.

### 2.5  Identity & Access Management

The curator runs the proposal; requests are written by private readers only.

### 2.6  Observability

The register is a readable file; the summary counts candidates for the portal.

### 2.7  Governance & Policy Enforcement

Minimum documents and the covered-by rule are the admission policy.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | data | gold/<v>/candidates per document; ontology/requests |
| I2 | out | artefact | ontology/candidates/register.json; a revision draft one minor version up |

### 3.4  Capability dependencies (requires)

- ABB-009 (1): Candidates come from extraction
- ABB-017 (0..1): Requests come from the workbench
- ABB-006 (1): A proposal is a draft for publish

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/ontology/candidates.py; workbench.requested_terms` |
| Capabilities | CAP-003, CAP-012 |
| Context | BC-002 |

## 5  Solution Building Block guidance

Realised in the pipeline image and the CLI.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
