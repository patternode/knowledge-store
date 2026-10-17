---
kind: abb
id: ABB-015
title: "ABB-015 Claim grounding and checks"
short_name: "GROUND"
description: "The control that makes an answer safe to show: each citation checked by code against a source the caller may read, each kept claim checked by the guardrail for contextual grounding, failures repaired once, and the answer rendered from what survived."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Answering"
part_of: BC-005
realises_capabilities: [CAP-008]
realised_by: [SBB-006]
requires:
  - { abb: ABB-012, cardinality: "1", rationale: "Re-reads through the tools" }
  - { abb: ABB-010, cardinality: "1", rationale: "Cells and snapshots to check against" }
domains: [application]
interfaces:
  - { id: "I1", direction: "in", type: "query", description: "Proposed claims; the re-read passages, cells and figures" }
  - { id: "I2", direction: "out", type: "query", description: "Kept claims, failures with reasons, the rendered answer with numbered sources, or an abstention" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/agent/grounding.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-015 Claim grounding and checks

| Property | Value |
|---|---|
| ABB ID | ABB-015 |
| ABB Name | Claim grounding and checks |
| Short Name | GROUND |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Answering |
| Bounded context | BC-005 |
| Realises | CAP-008 |
| Realised by | SBB-006 |

The control that makes an answer safe to show: each citation checked by code against a source the caller may read, each kept claim checked by the guardrail for contextual grounding, failures repaired once, and the answer rendered from what survived.

## 1  Purpose

No statement without a source (ADR-002). The checks are deterministic, tested without a model, and the only path to the page.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Passage check.** Exists and readable; quote found after normalising; at least twelve characters
- **Cell check.** Exists, not invalid, value equal by type
- **Figure check.** Recomputed per citation; numbers numerically; averages rounded as stated
- **Guardrail.** Contextual grounding on each kept claim with the passage, the row or the computation as source
- **Render.** Distinct sources numbered; claims as text with references; abstain when none

### 2.3  Attributes

- **Determinism.** Same inputs, same verdict
- **Testability.** The test suite runs the checks with a fake model

### 2.4  Semantic

Inside: checking and rendering. Outside: proposing (ABB-014).

### 2.5  Identity & Access Management

Re-reads use the caller's token, so a private passage fails for a public caller.

### 2.6  Observability

The grounding report: proposed, shown, repairs, failures, guardrail drops.

### 2.7  Governance & Policy Enforcement

Thresholds are deployment inputs; the rule itself is code.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | data | Proposed claims; the re-read passages, cells and figures |
| I2 | out | data | Kept claims, failures with reasons, the rendered answer with numbered sources, or an abstention |

### 3.4  Capability dependencies (requires)

- ABB-012 (1): Re-reads through the tools
- ABB-010 (1): Cells and snapshots to check against

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/agent/grounding.py; agent/valves.py (Guardrail)` |
| Capabilities | CAP-008 |
| Context | BC-005 |

## 5  Solution Building Block guidance

Realised in the agent image with Bedrock Guardrails (SBB-006).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
