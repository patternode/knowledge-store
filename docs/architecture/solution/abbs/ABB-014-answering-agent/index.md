---
kind: abb
id: ABB-014
title: "ABB-014 Answering agent"
short_name: "AGENT"
description: "The container that answers: it plans in the ontology's terms, calls the fixed tools as the person asking, proposes claims with citations, re-reads and checks every citation, repairs once, applies the guardrail, and shows nothing unchecked, under valves and with every step recorded and priced."
version: 0.2.0
status: draft
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Answering"
part_of: BC-005
realises_capabilities: [CAP-008, CAP-010, CAP-012]
realised_by: [SBB-006]
requires:
  - { abb: ABB-026, cardinality: "1", rationale: "Every tool call goes through the gateway as the caller" }
  - { abb: ABB-012, cardinality: "1", rationale: "The graph and structured tools" }
  - { abb: ABB-025, cardinality: "1", rationale: "Passage search and read" }
  - { abb: ABB-020, cardinality: "1", rationale: "Accepts only the deployment's own tokens" }
domains: [application]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "question, collection, history, mode, as the caller, with a session id (CT-004)" }
  - { id: "I2", direction: "out", type: "query", description: "answer, claims, sources, gaps, grounding report, steps, usage, cost; steps streamed as server-sent events" }
  - { id: "I3", direction: "out", type: "request", description: "Tool calls over MCP as the caller (CT-002, CT-003)" }
  - { id: "I4", direction: "out", type: "request", description: "Model and guardrail calls, each priced into the ledger" }
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
| Status | draft, reversed from the implementation at 0.3.0, recalibrated to container grain |
| Category | Answering |
| Bounded context | BC-005 |
| Realises | CAP-008, CAP-010, CAP-012 |
| Realised by | SBB-006 |
| Grain | One C4 container: passes the container test of the [calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md) |

The container that answers: it plans in the ontology's terms, calls the fixed tools as the person asking, proposes claims with citations, re-reads and checks every citation, repairs once, applies the guardrail, and shows nothing unchecked, under valves and with every step recorded and priced.

This block absorbed ABB-015 Claim grounding and checks, ABB-016 Valves and quotas, ABB-017 Workbench, ABB-022 Model access and ledger under the [calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md): each ran inside this container's process and none passed the container test, so each is a component row below and its identifier is retired.

## 1  Purpose

The model is a proposer. Giving it the ontology, fixed tools and a claim schema makes what it proposes checkable; giving it the caller's token makes what it reads lawful; checking in code before anything is shown is ADR-002. The checks, the valves, the recorder and the model client run in the agent's own process, so they are its components.

## 2  Building block

### 2.1  Component Diagram

The components below are the boxes of this container's component diagram, which is not yet drawn. The outside view of this block is its box in [AP-001](../../patterns/AP-001-ontology-driven-graphrag/index.md) and the row of its SBB in [RA-001](../../patterns/RA-001-knowledge-store-on-aws/index.md).

### 2.2  Components

- **Admission.** Token required; the daily count read before any work
- **Prompt.** The agent rendition of the active ontology version, the collection and the applicable table questions
- **Tool loop.** Strands with hooks for limits and steps; structured output GroundedAnswer
- **Re-read.** Cited passages, cells and figures fetched again as the caller
- **Repair.** Failures sent back once with their reasons
- **Analyst.** A second mode with the GapReport schema, kept as an ontology request
- **Streaming.** Steps then the result over server-sent events
- **Passage check.** Exists and readable; quote found after normalising; at least twelve characters (folded from ABB-015 Claim grounding and checks)
- **Cell check.** Exists, not invalid, value equal by type (folded from ABB-015 Claim grounding and checks)
- **Figure check.** Recomputed per citation; numbers numerically; averages rounded as stated (folded from ABB-015 Claim grounding and checks)
- **Guardrail.** Contextual grounding on each kept claim with the passage, the row or the computation as source (folded from ABB-015 Claim grounding and checks)
- **Render.** Distinct sources numbered; claims as text with references; abstain when none (folded from ABB-015 Claim grounding and checks)
- **Per-question hooks.** Cancel a tool call or a model call past the budget; the agent answers from what it has (folded from ABB-016 Valves and quotas)
- **Daily counts.** Conditional writes keyed by subject and day; exempt service clients (folded from ABB-016 Valves and quotas)
- **Table questions.** The catalogue questions added to the prompt when the mapping supports them (folded from ABB-016 Valves and quotas)
- **Recorder.** Steps with readable titles per tool; streamed (folded from ABB-017 Workbench)
- **Pricing.** Usage per model step priced from the ledger's table (folded from ABB-017 Workbench)
- **Term usage.** queried, read, cited per kind and term; totals all time and per month (folded from ABB-017 Workbench)
- **Analyst.** Verdicts answerable, data missing, ontology missing, extraction missed, out of scope; proposed terms (folded from ABB-017 Workbench)
- **Requests.** Kept reports as files the candidate register reads (folded from ABB-017 Workbench)
- **Provider seam.** bedrock or anthropic; model name mapping; parameters a model rejects dropped per family; throttling mapped to one exception (folded from ABB-022 Model access and ledger)
- **Ledger client.** Wraps any Converse client; buffers; flushes to usage/ledger/dt=<day>/ (folded from ABB-022 Model access and ledger)
- **Prices.** A table of list prices with batch and regional factors (folded from ABB-022 Model access and ledger)
- **Strands model.** The same choice for the agent framework (folded from ABB-022 Model access and ledger)

### 2.3  Attributes

- **Statelessness.** History in the payload; the session id carries no subject
- **Boundedness.** Every call under a valve
- **Nothing unchecked.** A claim that fails its check is repaired once or dropped; abstention is a stated answer

### 2.4  Semantic

Inside: planning, proposing, checking, repairing, limiting, recording and pricing. Outside: the tools (ABB-012, ABB-025) behind the gateway (ABB-026), the API that invokes it (ABB-019) and the page that shows the result (ABB-018).

### 2.5  Identity & Access Management

Accepts only tokens from the deployment's portal and service clients; presents the same token to the gateway; invokes the model and the guardrail with its own role, with model grants scoped to the configured ids.

### 2.6  Observability

Every model and tool call is a step with duration, usage and price; traces and metrics to CloudWatch; the ledger row per call.

### 2.7  Governance & Policy Enforcement

Prompt attack and content filters on the question; contextual grounding by the guardrail; the structured output schema is the contract; the valves (tool calls, model calls, output tokens, repairs, questions per day) are deployment inputs.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | request | question, collection, history, mode, as the caller, with a session id (CT-004) |
| I2 | out | query | answer, claims, sources, gaps, grounding report, steps, usage, cost; steps streamed as server-sent events |
| I3 | out | request | Tool calls over MCP as the caller (CT-002, CT-003) |
| I4 | out | request | Model and guardrail calls, each priced into the ledger |

### 3.4  Capability dependencies (requires)

- ABB-026 (1): Every tool call goes through the gateway as the caller
- ABB-012 (1): The graph and structured tools
- ABB-025 (1): Passage search and read
- ABB-020 (1): Accepts only the deployment's own tokens

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/agent/app.py, grounding.py, valves.py, quota.py; workbench.py; llm.py, ledger.py` |
| Capabilities | CAP-008, CAP-010, CAP-012 |
| Context | BC-005 |

## 5  Solution Building Block guidance

Realised on AgentCore Runtime with Strands, Bedrock models and Guardrails (SBB-006). The Chat API's fallback loop (ABB-019) is the transitional realisation until the Runtime exists in a deployment; the command line runs it in process (ABB-028).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain: absorbed ABB-015, ABB-016, ABB-017, ABB-022 |
