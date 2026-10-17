---
kind: abb
id: ABB-014
title: "ABB-014 Answering agent"
short_name: "AGENT"
description: "The agent that plans in the ontology's terms, calls the fixed tools as the person asking, proposes claims with citations as structured output, and hands them to the checks; also the analyst that says what it would take."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Answering"
part_of: BC-005
realises_capabilities: [CAP-008]
realised_by: [SBB-006, SBB-007, SBB-013]
requires:
  - { abb: ABB-012, cardinality: "1", rationale: "The tools" }
  - { abb: ABB-013, cardinality: "1", rationale: "Passage search" }
  - { abb: ABB-015, cardinality: "1", rationale: "Nothing is shown unchecked" }
  - { abb: ABB-016, cardinality: "1", rationale: "Runs under the valves" }
  - { abb: ABB-022, cardinality: "1", rationale: "The model" }
domains: [application]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "question, collection, history, mode, as the caller (CT-004)" }
  - { id: "I2", direction: "out", type: "query", description: "answer, claims, sources, gaps, grounding report, steps, usage, cost; streamed steps" }
  - { id: "I3", direction: "out", type: "request", description: "Tool calls as the caller" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/agent/app.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-014 Answering agent

| Property | Value |
|---|---|
| ABB ID | ABB-014 |
| ABB Name | Answering agent |
| Short Name | AGENT |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Answering |
| Bounded context | BC-005 |
| Realises | CAP-008 |
| Realised by | SBB-006, SBB-007, SBB-013 |

The agent that plans in the ontology's terms, calls the fixed tools as the person asking, proposes claims with citations as structured output, and hands them to the checks; also the analyst that says what it would take.

## 1  Purpose

The model is a proposer. Giving it the ontology, fixed tools and a claim schema makes what it proposes checkable; giving it the caller's token makes what it reads lawful.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Admission.** Token required; daily count
- **Prompt.** The agent rendition, the collection and version, the applicable table questions
- **Tool loop.** Strands with hooks for limits and steps; structured output GroundedAnswer
- **Re-read.** Cited passages, cells and figures fetched again as the caller
- **Repair.** Failures sent back once
- **Analyst.** A second mode with the GapReport schema
- **Streaming.** Steps then the result over server-sent events

### 2.3  Attributes

- **Statelessness.** History in the payload; the session id carries no subject
- **Boundedness.** Every call under a valve

### 2.4  Semantic

Inside: planning, proposing, repairing. Outside: the checks themselves (ABB-015) and the page (ABB-018).

### 2.5  Identity & Access Management

Accepts only tokens from the portal's and service clients; presents the same token to the Gateway; invokes the model and the guardrail with its own role.

### 2.6  Observability

Every model and tool call is a step with duration, usage and price; traces and metrics to CloudWatch.

### 2.7  Governance & Policy Enforcement

Prompt attack and content filters on the question; the structured output schema is the contract.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | request | question, collection, history, mode, as the caller (CT-004) |
| I2 | out | result | answer, claims, sources, gaps, grounding report, steps, usage, cost; streamed steps |
| I3 | out | request | Tool calls as the caller |

### 3.4  Capability dependencies (requires)

- ABB-012 (1): The tools
- ABB-013 (1): Passage search
- ABB-015 (1): Nothing is shown unchecked
- ABB-016 (1): Runs under the valves
- ABB-022 (1): The model

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/agent/app.py; portal_api/chat.py (the fallback loop)` |
| Capabilities | CAP-008 |
| Context | BC-005 |

## 5  Solution Building Block guidance

Realised on AgentCore Runtime with Strands (SBB-006); the portal's loop (SBB-007) is the transitional realisation; local in process (SBB-013).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
