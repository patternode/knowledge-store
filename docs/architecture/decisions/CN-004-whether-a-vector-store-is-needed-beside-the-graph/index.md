---
kind: consideration
id: CN-004
title: "CN-004 Whether a vector store is needed beside the graph"
version: 0.1.0
status: accepted
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
consideration_status: resolved
question: "Do questions that describe a situation need search by meaning, or does the graph with keyword search suffice?"
options:
  - { name: "Graph and keyword only", summary: "No index to run" }
  - { name: "A passage index by meaning", summary: "One vector per passage" }
criteria:
  - "Recall on frontline questions"
  - "Cost at rest"
resolved_by: ADR-007
affects: [CAP-006, ABB-013, ABB-025]
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# CN-004 Whether a vector store is needed beside the graph

Do questions that describe a situation need search by meaning, or does the graph with keyword search suffice?

| Option | Summary |
|---|---|
| Graph and keyword only | No index to run |
| A passage index by meaning | One vector per passage |

Criteria: Recall on frontline questions; Cost at rest.

Status: resolved, resolved by ADR-007. Affects CAP-006, ABB-013, ABB-025.

Resolved: yes, on S3 Vectors, switchable off.
