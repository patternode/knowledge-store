---
kind: abb
id: ABB-021
title: "ABB-021 Evaluation runner"
short_name: "EVAL"
description: "The command that runs a set of questions against a lake or a deployed chat, scores each answer deterministically against the facts it must and must not state and the sources it should cite, and reports."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Evaluation"
part_of: BC-007
realises_capabilities: [CAP-011]
realised_by: [SBB-019]
requires:
  - { abb: ABB-014, cardinality: "1", rationale: "Asks the agent" }
  - { abb: ABB-019, cardinality: "0..1", rationale: "Through the API, as a person" }
domains: [application]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "An evaluation set (CT-009)" }
  - { id: "I2", direction: "out", type: "query", description: "report.md and results.json with the four outcomes" }
  - { id: "I3", direction: "out", type: "request", description: "Questions to the agent in process or through POST /api/chat as a person" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/evaluation/domain/score.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-021 Evaluation runner

| Property | Value |
|---|---|
| ABB ID | ABB-021 |
| ABB Name | Evaluation runner |
| Short Name | EVAL |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0, recalibrated to container grain |
| Category | Evaluation |
| Bounded context | BC-007 |
| Realises | CAP-011 |
| Realised by | SBB-019 |
| Grain | One C4 container: passes the container test of the [calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md) |

The command that runs a set of questions against a lake or a deployed chat, scores each answer deterministically against the facts it must and must not state and the sources it should cite, and reports.

## 1  Purpose

Right is not grounded. A set and a scorer make a release comparable with the last and a collection's gaps countable. It is its own container, a command with its own run and release, apart from the operator command line because evaluators run it without operating the store.

## 2  Building block

### 2.1  Component Diagram

The components below are the boxes of this container's component diagram, which is not yet drawn. The outside view of this block is its box in [AP-001](../../patterns/AP-001-ontology-driven-graphrag/index.md) and the row of its SBB in [RA-001](../../patterns/RA-001-knowledge-store-on-aws/index.md).

### 2.2  Components

- **Set loader.** Validation of ids, kinds and fields
- **Targets.** In-process with local tools; the API with a person's token
- **Scorer.** Word-boundary matching with case and dashes folded; order; abstention
- **Report.** Overall and per question, with a cost estimate before a run

### 2.3  Attributes

- **Determinism.** No model judges
- **Cost awareness.** An estimate before a run

### 2.4  Semantic

Inside: running and scoring. Outside: writing good sets, and the agent that answers.

### 2.5  Identity & Access Management

A run through the API counts against the person's quota; in process it uses the operator's credentials.

### 2.6  Observability

The report is the observation.

### 2.7  Governance & Policy Enforcement

Sets ship as examples; a deployment keeps its own.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | request | An evaluation set (CT-009) |
| I2 | out | query | report.md and results.json with the four outcomes |
| I3 | out | request | Questions to the agent in process or through POST /api/chat as a person |

### 3.4  Capability dependencies (requires)

- ABB-014 (1): Asks the agent
- ABB-019 (0..1): Through the API, as a person

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/evaluation/domain/score.py, run.py; examples/evals` |
| Capabilities | CAP-011 |
| Context | BC-007 |

## 5  Solution Building Block guidance

Realised as a command on an operator's machine (SBB-019).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain |
