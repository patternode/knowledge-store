---
kind: abb
id: ABB-017
title: "ABB-017 Workbench"
short_name: "BENCH"
description: "Showing how an answer was found and what it cost, counting which ontology terms questions ask for, read and cite, and turning a question the store could not answer into a gap report a curator can keep as an ontology request."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Answering"
part_of: BC-005
realises_capabilities: [CAP-012]
realised_by: [SBB-006, SBB-007]
requires:
  - { abb: ABB-014, cardinality: "1", rationale: "Records the agent's steps" }
  - { abb: ABB-022, cardinality: "1", rationale: "Prices from the ledger" }
domains: [application, business]
interfaces:
  - { id: "I1", direction: "in", type: "event", description: "Model calls, tool calls, checks, repairs, guardrail verdicts" }
  - { id: "I2", direction: "out", type: "query", description: "Steps with timing, usage and price; term usage counters; a gap report; an ontology request (CT-001 /requests)" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/workbench.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-017 Workbench

| Property | Value |
|---|---|
| ABB ID | ABB-017 |
| ABB Name | Workbench |
| Short Name | BENCH |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Answering |
| Bounded context | BC-005 |
| Realises | CAP-012 |
| Realised by | SBB-006, SBB-007 |

Showing how an answer was found and what it cost, counting which ontology terms questions ask for, read and cite, and turning a question the store could not answer into a gap report a curator can keep as an ontology request.

## 1  Purpose

A curator improves an ontology they can see used. The workbench is the feedback loop from answering to the next version.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Recorder.** Steps with readable titles per tool; streamed
- **Pricing.** Usage per model step priced from the ledger's table
- **Term usage.** queried, read, cited per kind and term; totals all time and per month
- **Analyst.** Verdicts answerable, data missing, ontology missing, extraction missed, out of scope; proposed terms
- **Requests.** Kept reports as files the candidate register reads

### 2.3  Attributes

- **Privacy.** Term names are kept, never questions
- **Immediacy.** Steps appear while the answer runs

### 2.4  Semantic

Inside: observation and feedback. Outside: the answer itself.

### 2.5  Identity & Access Management

Requests are for private readers.

### 2.6  Observability

It is the observability of answering.

### 2.7  Governance & Policy Enforcement

Usage totals never expire; a request is a curated artefact.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | event | Model calls, tool calls, checks, repairs, guardrail verdicts |
| I2 | out | data | Steps with timing, usage and price; term usage counters; a gap report; an ontology request (CT-001 /requests) |

### 3.4  Capability dependencies (requires)

- ABB-014 (1): Records the agent's steps
- ABB-022 (1): Prices from the ledger

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/workbench.py; chat/app.js (the panel)` |
| Capabilities | CAP-012 |
| Context | BC-005 |

## 5  Solution Building Block guidance

Realised in the agent image, the portal Lambda and the chat page.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
