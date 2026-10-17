---
kind: abb
id: ABB-022
title: "ABB-022 Model access and ledger"
short_name: "MODEL"
description: "One client every job uses, speaking the Converse shape, over Bedrock or the Anthropic API by configuration, with every call priced into a ledger in the lake."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Platform services"
part_of: BC-008
realises_capabilities: [CAP-010]
realised_by: [SBB-012]
requires: []
domains: [technology]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "A Converse-shaped request from any caller" }
  - { id: "I2", direction: "out", type: "query", description: "A Converse-shaped response, from Bedrock or the Anthropic Messages API" }
  - { id: "I3", direction: "out", type: "query", description: "A ledger row per call: tokens, list-price cost, latency, outcome, job and run" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/llm.py, ledger.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-022 Model access and ledger

| Property | Value |
|---|---|
| ABB ID | ABB-022 |
| ABB Name | Model access and ledger |
| Short Name | MODEL |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Platform services |
| Bounded context | BC-008 |
| Realises | CAP-010 |
| Realised by | SBB-012 |

One client every job uses, speaking the Converse shape, over Bedrock or the Anthropic API by configuration, with every call priced into a ledger in the lake.

## 1  Purpose

A change of provider, model or price is made once. Metering at the client is what makes the cost of a question and of a sweep knowable.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Provider seam.** bedrock or anthropic; model name mapping; parameters a model rejects dropped per family; throttling mapped to one exception
- **Ledger client.** Wraps any Converse client; buffers; flushes to usage/ledger/dt=<day>/
- **Prices.** A table of list prices with batch and regional factors
- **Strands model.** The same choice for the agent framework

### 2.3  Attributes

- **Uniformity.** Every caller the same shape
- **Metering.** Failures recorded too

### 2.4  Semantic

Inside: the client and the ledger. Outside: what callers ask.

### 2.5  Identity & Access Management

The Bedrock model grants are scoped to the configured model id; the Anthropic key is a secret read at run time.

### 2.6  Observability

The ledger and its report command.

### 2.7  Governance & Policy Enforcement

Model ids are explicit inputs; the provider is a choice recorded per deployment.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | request | A Converse-shaped request from any caller |
| I2 | out | response | A Converse-shaped response, from Bedrock or the Anthropic Messages API |
| I3 | out | data | A ledger row per call: tokens, list-price cost, latency, outcome, job and run |

### 3.4  Capability dependencies (requires)

None beyond the cross-cutting trio.

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/llm.py, ledger.py` |
| Capabilities | CAP-010 |
| Context | BC-008 |

## 5  Solution Building Block guidance

Realised by Bedrock in the account's region or the Anthropic API (SBB-012).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
