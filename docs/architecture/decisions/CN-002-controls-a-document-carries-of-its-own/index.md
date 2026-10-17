---
kind: consideration
id: CN-002
title: "CN-002 Controls a document carries of its own"
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
consideration_status: open
question: "How do a source document's permissions, protection and classification travel with its passages and decide what an answer may show, beyond the public or private scope?"
options:
  - { name: "Keep scope only", summary: "Two values per source; simple, applied everywhere" }
  - { name: "Entitlements and classification from the source", summary: "An envelope per item, a control record, enforcement replacing the boolean, as designed in source-controls.md" }
  - { name: "A policy engine at the tools", summary: "Evaluate a policy per call" }
criteria:
  - "No gap in enforcement"
  - "Steward effort per source"
  - "Cost per call"
affects: [CAP-009, ABB-020, ABB-001]
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# CN-002 Controls a document carries of its own

How do a source document's permissions, protection and classification travel with its passages and decide what an answer may show, beyond the public or private scope?

| Option | Summary |
|---|---|
| Keep scope only | Two values per source; simple, applied everywhere |
| Entitlements and classification from the source | An envelope per item, a control record, enforcement replacing the boolean, as designed in source-controls.md |
| A policy engine at the tools | Evaluate a policy per call |

Criteria: No gap in enforcement; Steward effort per source; Cost per call.

Status: open. Affects CAP-009, ABB-020, ABB-001.

The design, its open decisions and its implementation order are in docs/architecture/source-controls.md; ADR-010 records the current choice.
