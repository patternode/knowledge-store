---
kind: abb
id: ABB-021
title: "ABB-021 Evaluation runner and scorer"
short_name: "EVAL"
description: "Runs a set of questions against a lake or the deployed chat, scores each answer deterministically against the facts it must and must not state and the sources it should cite, and reports the four outcomes."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Evaluation"
part_of: BC-007
realises_capabilities: [CAP-011]
realised_by: [SBB-013, SBB-007]
requires:
  - { abb: ABB-014, cardinality: "1", rationale: "Asks the agent" }
  - { abb: ABB-019, cardinality: "0..1", rationale: "Through the API, as a person" }
domains: [application, business]
interfaces:
  - { id: "I1", direction: "in", type: "query", description: "An evaluation set (CT-009)" }
  - { id: "I2", direction: "out", type: "query", description: "report.md and results.json" }
  - { id: "I3", direction: "out", type: "request", description: "Questions to the agent in process or POST /api/chat" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/evals/score.py, run.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-021 Evaluation runner and scorer

| Property | Value |
|---|---|
| ABB ID | ABB-021 |
| ABB Name | Evaluation runner and scorer |
| Short Name | EVAL |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Evaluation |
| Bounded context | BC-007 |
| Realises | CAP-011 |
| Realised by | SBB-013, SBB-007 |

Runs a set of questions against a lake or the deployed chat, scores each answer deterministically against the facts it must and must not state and the sources it should cite, and reports the four outcomes.

## 1  Purpose

Right is not grounded. A set and a scorer make a release comparable with the last and a collection's gaps countable.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Set loader.** Validation of ids, kinds and fields
- **Targets.** In-process with local tools; the API with a person's token
- **Scorer.** Word-boundary matching with case and dashes folded; order; abstention
- **Report.** Overall and per kind; per question

### 2.3  Attributes

- **Determinism.** No model judges
- **Cost awareness.** An estimate before a run

### 2.4  Semantic

Inside: running and scoring. Outside: writing good sets.

### 2.5  Identity & Access Management

A run through the API counts against the person's quota.

### 2.6  Observability

The report is the observation.

### 2.7  Governance & Policy Enforcement

Sets ship as examples; a deployment keeps its own.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | artefact | An evaluation set (CT-009) |
| I2 | out | artefact | report.md and results.json |
| I3 | out | request | Questions to the agent in process or POST /api/chat |

### 3.4  Capability dependencies (requires)

- ABB-014 (1): Asks the agent
- ABB-019 (0..1): Through the API, as a person

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/evals/score.py, run.py; examples/evals` |
| Capabilities | CAP-011 |
| Context | BC-007 |

## 5  Solution Building Block guidance

Realised as a command (SBB-013) that targets the portal (SBB-007).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
