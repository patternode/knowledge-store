---
kind: consideration
id: CN-005
title: "CN-005 Where the projection and the chat state live at scale"
version: 0.1.0
status: accepted
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
consideration_status: resolved
question: "When one process's memory and one DynamoDB table are not enough, what holds the projection and the chat state?"
options:
  - { name: "Memory and DynamoDB", summary: "The defaults" }
  - { name: "MongoDB for both", summary: "The portal holds nothing in memory and scales out" }
  - { name: "A graph backend for traversals", summary: "Neo4j or AGE" }
criteria:
  - "Idle cost"
  - "Scale-out"
  - "Compatibility of wire-compatible services"
resolved_by: ADR-008
affects: [CAP-005, ABB-011, ABB-019]
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# CN-005 Where the projection and the chat state live at scale

When one process's memory and one DynamoDB table are not enough, what holds the projection and the chat state?

| Option | Summary |
|---|---|
| Memory and DynamoDB | The defaults |
| MongoDB for both | The portal holds nothing in memory and scales out |
| A graph backend for traversals | Neo4j or AGE |

Criteria: Idle cost; Scale-out; Compatibility of wire-compatible services.

Status: resolved, resolved by ADR-008. Affects CAP-005, ABB-011, ABB-019.

Resolved by ADR-008: memory by default, backends by configuration.
