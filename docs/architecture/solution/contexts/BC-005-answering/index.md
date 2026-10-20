---
kind: bounded-context
id: BC-005
title: "BC-005 Answering"
description: "Questions, claims, citations, checks, valves and steps: taking a person's question to an answer made only of what passed, within limits, with the steps visible."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
part_of: PL-001
contains: [ABB-014]
realises_capabilities: [CAP-008, CAP-010, CAP-012]
subdomain_kind: core
c4_levels: [container, component]
ubiquitous_language:
  - { term: "Question", definition: "At most 2,000 characters, with up to six turns of history carried in the payload" }
  - { term: "Claim", definition: "One statement the model proposes, with one or more citations" }
  - { term: "Citation", definition: "A passage id with a verbatim quote; a cell id with a value; a metric id with a figure and its computation" }
  - { term: "Check", definition: "Code re-reads the citation as the caller and tests quote, value or recomputation; the guardrail tests contextual grounding" }
  - { term: "Repair", definition: "One round in which failures go back to the agent with their reasons" }
  - { term: "Abstain", definition: "No claim left: a stated refusal naming what was missing" }
  - { term: "Valve", definition: "A limit set at deployment: tool calls, model calls, output tokens, repairs, questions per day" }
  - { term: "Step", definition: "One recorded event of answering: model call, tool call, check, repair, guardrail, done, error; streamed and priced" }
  - { term: "Gap report", definition: "The analyst's verdict on a question the store could not answer, with the terms and data it would take" }
relationships:
  - { with: BC-004, pattern: open-host-service, role: downstream }
  - { with: BC-006, pattern: customer-supplier, role: downstream }
  - { with: BC-002, pattern: customer-supplier, role: upstream }
  - { with: BC-008, pattern: conformist, role: downstream }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# BC-005 Answering

| Property | Value |
|---|---|
| Context ID | BC-005 |
| Platform | PL-001 Knowledge Store |
| Owner team | Patternode (Dermot O'Brien) |
| Subdomain | core |
| Realises | CAP-008, CAP-010, CAP-012 |
| Contains | ABB-014 |

Questions, claims, citations, checks, valves and steps: taking a person's question to an answer made only of what passed, within limits, with the steps visible.

## Ubiquitous language

| Term | Meaning in this context |
|---|---|
| Question | At most 2,000 characters, with up to six turns of history carried in the payload |
| Claim | One statement the model proposes, with one or more citations |
| Citation | A passage id with a verbatim quote; a cell id with a value; a metric id with a figure and its computation |
| Check | Code re-reads the citation as the caller and tests quote, value or recomputation; the guardrail tests contextual grounding |
| Repair | One round in which failures go back to the agent with their reasons |
| Abstain | No claim left: a stated refusal naming what was missing |
| Valve | A limit set at deployment: tool calls, model calls, output tokens, repairs, questions per day |
| Step | One recorded event of answering: model call, tool call, check, repair, guardrail, done, error; streamed and priced |
| Gap report | The analyst's verdict on a question the store could not answer, with the terms and data it would take |

## Where the model lives today

- `answering/domain/` (grounding: the claim models and checks; valves: every limit and the table questions)
- `answering/ports.py` (QuestionScreen, ClaimVerifier)
- `answering/slices/workbench.py` (steps, term usage, cost, the analyst prompt and report, term requests)
- `answering/adapters/` (agent_app: the agent loop on Strands; bedrock_guardrail: the question screen and claim verifier; agent_client; fallback_chat: the portal's own tool loop)
- `apps/agent.py`: AgentCore Runtime's entry point, composing the agent with Access's quota

Two answering paths exist: the agent on the Runtime with structured output and full checks, and the portal's own loop with citation markers and no claim-level check, used until the Runtime is switched on. The context's rules are the agent's; the loop is a transitional implementation (CN-006).

## Relationships with other contexts

| With | Pattern | Role | Why |
|---|---|---|---|
| BC-004 | open-host-service | downstream | Calls the fixed tools as the caller |
| BC-006 | customer-supplier | downstream | Invoked by the chat API as the person; returns the answer and steps |
| BC-002 | customer-supplier | upstream | Ontology requests to the candidate register |
| BC-008 | conformist | downstream | Model access and prices as given |

## Building blocks

ABB-014 Answering agent, a page under [../abbs](../../abbs/README.md). The checks, the valves, the workbench recorder and the model client are its components; the first pass's ABB-015, ABB-016, ABB-017 and ABB-022 are rows in its document, retired under the calibration standard.
