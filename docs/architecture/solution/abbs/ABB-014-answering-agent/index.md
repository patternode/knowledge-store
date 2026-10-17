---
kind: abb
id: ABB-014
title: "ABB-014 Answering agent"
short_name: "AGENT"
description: "The agent as one deployable unit: plans in the ontology's terms, calls the fixed tools as the person asking, proposes claims with citations as structured output, checks every citation by code and every claim by the guardrail before anything is shown, runs under its valves, records its steps and cost for the workbench, and in its analyst mode says what it would take to answer."
version: 0.2.0
status: draft
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Answering"
part_of: BC-005
realises_capabilities: [CAP-008]
realised_by: [SBB-006]
requires:
  - { abb: ABB-012, cardinality: "1", rationale: "The tools, called as the caller" }
  - { abb: ABB-013, cardinality: "0..1", rationale: "Passage search, through the tools" }
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
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Answering |
| Bounded context | BC-005 |
| Realises | CAP-008 |
| Realised by | SBB-006 |

The agent as one deployable unit: plans in the ontology's terms, calls the fixed tools as the person asking, proposes claims with citations as structured output, checks every citation by code and every claim by the guardrail before anything is shown, runs under its valves, records its steps and cost for the workbench, and in its analyst mode says what it would take to answer.

## 1  Purpose

The model is a proposer. Giving it the ontology, fixed tools and a claim schema makes what it proposes checkable; giving it the caller's token makes what it reads lawful.

## 2  Building block

### 2.1  Component Diagram

The components below are what runs inside this one container, listed per the building block calibration standard: none of them is a building block of its own. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Admission.** Token required; the daily count at the agent as well as the portal
- **Prompt.** The agent rendition, the collection and version, the applicable table questions
- **Tool loop.** Strands with hooks for limits and steps; structured output GroundedAnswer
- **Checks.** Passage check (exists, readable, quote found after normalising, at least twelve characters); cell check (exists, value equal by type); figure check (recomputed per citation); the guardrail's contextual grounding on each kept claim
- **Repair and render.** Failures sent back once; distinct sources numbered; claims as text with references; abstain when none survive
- **Valves.** Per-question hooks that cancel a tool call or a model call past the budget, so the agent answers from what it has; question length and history caps
- **Recorder.** Steps with readable titles per tool, streamed; usage per model step priced from the ledger's table; term usage queried, read and cited per kind
- **Analyst.** A second mode with the GapReport schema: answerable, data missing, ontology missing, extraction missed, out of scope; proposed terms kept as requests the candidate register reads
- **Model client.** The same Converse-shaped client as the sweep, over Bedrock or the Anthropic API, every call priced into the ledger
- **Streaming.** Steps then the result over server-sent events

### 2.3  Attributes

- **Statelessness.** History in the payload; the session id carries no subject
- **Boundedness.** Every call under a valve

### 2.4  Semantic

Inside: proposing, checking, limiting and recording, all in one process. Outside: the page that shows the answer (ABB-018), the API that admits the question and counts the quota (ABB-019), and the tools (ABB-012).

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

- ABB-012 (1): The tools, called as the caller
- ABB-013 (0..1): Passage search, through the tools

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/agent/app.py, grounding.py, valves.py, quota.py; workbench.py; llm.py, ledger.py; portal_api/chat.py (the fallback loop)` |
| Capabilities | CAP-008 |
| Context | BC-005 |

## 5  Solution Building Block guidance

Realised on AgentCore Runtime with Strands, Bedrock models and Guardrails (SBB-006). The chat API's fallback loop (ABB-019) and the in-process local agent (SBB-015) are transitional and local forms of the same components, not blocks of their own.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.2.0 | 2026-10-17 | Recalibrated to container grain: ABB-015, ABB-016 (the per-question valves), ABB-017 (the recorder and the analyst) and the agent's model client (ABB-022) folded in |
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
