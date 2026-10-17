---
kind: abb
id: ABB-016
title: "ABB-016 Valves and quotas"
short_name: "VALVE"
description: "Every limit in one place and enforced where it bites: per question in the agent's hooks, per person per day at the portal and again at the agent, per deployment in concurrency and throttling."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Answering"
part_of: BC-005
realises_capabilities: [CAP-010]
realised_by: [SBB-006, SBB-007]
requires:
  - { abb: ABB-019, cardinality: "1", rationale: "The portal counts questions per person" }
domains: [application]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "Limits from the environment: tool calls, model calls, output tokens, repairs, daily invocations" }
  - { id: "I2", direction: "out", type: "event", description: "A cancelled call past its budget; a refused question past the quota" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/agent/valves.py, quota.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-016 Valves and quotas

| Property | Value |
|---|---|
| ABB ID | ABB-016 |
| ABB Name | Valves and quotas |
| Short Name | VALVE |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Answering |
| Bounded context | BC-005 |
| Realises | CAP-010 |
| Realised by | SBB-006, SBB-007 |

Every limit in one place and enforced where it bites: per question in the agent's hooks, per person per day at the portal and again at the agent, per deployment in concurrency and throttling.

## 1  Purpose

Spend and runaway loops are stopped by structure rather than vigilance. A limit is an input of the module and a hook in the loop.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Per-question hooks.** Cancel a tool call or a model call past the budget; the agent answers from what it has
- **Daily counts.** Conditional writes keyed by subject and day; exempt service clients
- **Table questions.** The catalogue questions added to the prompt when the mapping supports them

### 2.3  Attributes

- **Transparency.** The limits are reported with the answer
- **Independence.** The agent's own count holds when the portal is bypassed

### 2.4  Semantic

Inside: the limits and the counts. Outside: pricing (ABB-022) and concurrency (infrastructure).

### 2.5  Identity & Access Management

The Runtime may update only agent# keys of the chat table.

### 2.6  Observability

Limits in every answer; refusals logged.

### 2.7  Governance & Policy Enforcement

Values are deployment inputs with stated defaults.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | config | Limits from the environment: tool calls, model calls, output tokens, repairs, daily invocations |
| I2 | out | control | A cancelled call past its budget; a refused question past the quota |

### 3.4  Capability dependencies (requires)

- ABB-019 (1): The portal counts questions per person

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/agent/valves.py, quota.py; portal_api/handler.py (take_quota)` |
| Capabilities | CAP-010 |
| Context | BC-005 |

## 5  Solution Building Block guidance

Realised in the agent image and the portal Lambda, with reserved concurrency and API throttling in Terraform.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
