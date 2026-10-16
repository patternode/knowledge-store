---
kind: capability
id: CAP-008
title: "CAP-008 Grounded answering"
description: "Taking a person's question to an answer made only of claims whose citations passed the checks, through an agent that plans in the ontology's terms, calls fixed tools as the caller, and abstains when the sources cannot answer."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
level: L2
parent: CAP-001
components:
  organisation: "The agent runs as the person asking; the product owner owns the checks"
  people: ["Readers", "Curators reading the workbench"]
  processes:
    - "Admit the caller and open the tools as them"
    - "Put the ontology rendition and the applicable table questions in the prompt"
    - "Run the tool loop under the valves with structured output"
    - "Re-read and check every citation; repair; apply the guardrail; render or abstain"
    - "Stream each step to the portal"
  technology: "Strands on AgentCore Runtime with Bedrock models, MCP tools through the Gateway, Pydantic claim models, Bedrock Guardrails contextual grounding, server-sent events; the portal's own Converse loop as the fallback"
maturity:
  current: 4
  target: 5
  assessment_date: 2026-10-16
  assessor: "Patternode (Dermot O'Brien), reversed from the implementation"
subdomain_kind: core
provided_by_platform: PL-001
realised_by_abbs: [ABB-014, ABB-015, ABB-016]
gaps:
  - "The portal's fallback loop resolves citation markers but runs no claim-level check (CN-006 notes it)"
  - "Sessions are stateless; history is six turns carried in the payload"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# CAP-008 Grounded answering

| Property | Value |
|---|---|
| Capability ID | CAP-008 |
| Level | L2 |
| Parent | CAP-001 |
| Status | Draft, reversed from the implementation at 0.3.0 |
| Subdomain | core |
| Maturity | 4, target 5 |
| Realised by | ABB-014, ABB-015, ABB-016 |

Taking a person's question to an answer made only of claims whose citations passed the checks, through an agent that plans in the ontology's terms, calls fixed tools as the caller, and abstains when the sources cannot answer.

## 1  Purpose

The model is a proposer, not a publisher. Its answer is a list of claims with citations; code re-reads every cited passage, cell and figure as the caller, checks quote, value and recomputation, runs the contextual grounding guardrail, repairs once, and shows only what survived.

## 2  Capability definition

| Dimension | For Knowledge Store |
|---|---|
| Organisation | The agent runs as the person asking; the product owner owns the checks |
| People | Readers, Curators reading the workbench |
| Processes | Admit the caller and open the tools as them; Put the ontology rendition and the applicable table questions in the prompt; Run the tool loop under the valves with structured output; Re-read and check every citation; repair; apply the guardrail; render or abstain; Stream each step to the portal |
| Technology | Strands on AgentCore Runtime with Bedrock models, MCP tools through the Gateway, Pydantic claim models, Bedrock Guardrails contextual grounding, server-sent events; the portal's own Converse loop as the fallback |

## 3  Sub-capabilities

| Sub-capability | What it covers | Status |
|---|---|---|
| Ontology-in-prompt planning | The released rendition and the table note | In place |
| Fixed tools as the caller | The person's token to the Gateway | In place |
| Claim checking | Passage, cell and figure checks; repair; guardrail | In place |
| Abstention | No claims left means a stated refusal | In place |
| Streaming | Steps as they happen | In place |

## 4  What the implementation does today

Claims cite a passage with a verbatim quote, a cell with a value, or a figure with its computation. The checks are in agent/grounding.py and tested without a model. A dropped claim is reported, an empty answer abstains and lists what was missing, and the agent's own daily count holds even when the portal is bypassed.

## 5  Maturity

Current maturity is 4 on the 0 to 5 scale, read from the implementation: the capability is defined, built and in service in the Patternode lab and in any deployment of the module. Target 5.

## 6  Gaps

- The portal's fallback loop resolves citation markers but runs no claim-level check (CN-006 notes it)
- Sessions are stateless; history is six turns carried in the payload
