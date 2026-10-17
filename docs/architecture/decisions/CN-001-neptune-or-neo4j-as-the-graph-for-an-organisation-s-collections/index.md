---
kind: consideration
id: CN-001
title: "CN-001 Neptune or Neo4j as the graph for an organisation's collections"
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
consideration_status: open
question: "Which graph store should hold an organisation's curated collections once they outgrow one process: Neptune as deployed, or Neo4j as the optional backend?"
options:
  - { name: "Neptune Database", summary: "The deployed SPARQL store; private, IAM-authenticated, the record's own model; about sixty dollars a month minimum" }
  - { name: "Neo4j or AuraDB", summary: "The optional property-graph backend; faster traversals at scale; a second model projected from the record" }
  - { name: "Neptune Serverless", summary: "Scales to zero-ish; the same model" }
criteria:
  - "Monthly floor"
  - "Traversal latency at the organisation's size"
  - "One model or two"
affects: [CAP-005, ABB-011, SBB-003, SBB-011]
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# CN-001 Neptune or Neo4j as the graph for an organisation's collections

Which graph store should hold an organisation's curated collections once they outgrow one process: Neptune as deployed, or Neo4j as the optional backend?

| Option | Summary |
|---|---|
| Neptune Database | The deployed SPARQL store; private, IAM-authenticated, the record's own model; about sixty dollars a month minimum |
| Neo4j or AuraDB | The optional property-graph backend; faster traversals at scale; a second model projected from the record |
| Neptune Serverless | Scales to zero-ish; the same model |

Criteria: Monthly floor; Traversal latency at the organisation's size; One model or two.

Status: open. Affects CAP-005, ABB-011, SBB-003, SBB-011.

The analysis with the managed services' limits and sources is docs/design/aws/scalability.md, whose recommendation is to stay on Neptune for the record and turn a backend on per collection; a decision record is owed when a deployment first needs it.
