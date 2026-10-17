---
kind: decision-record
id: ADR-003
title: "ADR-003 The person's identity goes all the way down"
version: 1.0.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
y_statement: "In the context of who the agent and the tools act as, facing the choice between a service identity with filtering in the prompt and the person's own verified token at every hop, we decided for the token all the way down (API Gateway, the Runtime, the Gateway with its interceptor) with one scope rule, and against a service identity, to achieve enforcement at the data rather than in the prompt, accepting the service clients of site sign-in as the one scoped exception and the operational cost of three authorisers."
decision_drivers: ["Prompt injection cannot widen access", "One scope rule", "Least privilege per hop"]
considered_options:
  - "A service identity with prompt-level filtering"
  - "The person's token at every hop"
  - "A service identity with a policy engine (Cedar) at the tools"
decision_outcome: "The person's token at every hop"
consequences:
  positive:
    - "The interceptor overwrites caller_private whatever the model wrote"
    - "No IAM grant from the portal to the Runtime: OAuth authorises"
  negative:
    - "Site sign-in needs two service clients"
    - "Token lifetimes bound a long answer"
change_type: introduce
affects_artefacts: [BC-006, ABB-020, ABB-027, ABB-012, ABB-025]
resolves: []
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ADR-003 The person's identity goes all the way down

Status: active, as implemented at 0.3.0. This record is reversed from the implementation and the design notes; the decision was made in the code and the notes before it was written here.

## Context

Most chat systems act as a service identity and filter at the edge; a prompt then becomes a way to read more than the person may.

## Decision

In the context of who the agent and the tools act as, facing the choice between a service identity with filtering in the prompt and the person's own verified token at every hop, we decided for the token all the way down (API Gateway, the Runtime, the Gateway with its interceptor) with one scope rule, and against a service identity, to achieve enforcement at the data rather than in the prompt, accepting the service clients of site sign-in as the one scoped exception and the operational cost of three authorisers.

## Options considered

- A service identity with prompt-level filtering
- The person's token at every hop
- A service identity with a policy engine (Cedar) at the tools

## Consequences

Positive: The interceptor overwrites caller_private whatever the model wrote; No IAM grant from the portal to the Runtime: OAuth authorises.

Negative: Site sign-in needs two service clients; Token lifetimes bound a long answer.

## Affects

BC-006, ABB-020, ABB-027, ABB-012, ABB-025.
