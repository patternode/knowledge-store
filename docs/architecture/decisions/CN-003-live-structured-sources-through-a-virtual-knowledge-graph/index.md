---
kind: consideration
id: CN-003
title: "CN-003 Live structured sources through a virtual knowledge graph"
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
consideration_status: resolved
resolved_by: ADR-009
question: "How should a table that lives in a database, rather than a file in the landing tree, be read in the ontology's terms?"
options:
  - { name: "Snapshots only", summary: "Export the table to a file and bind it; what exists" }
  - { name: "A virtual knowledge graph", summary: "Ontop over the R2RML the version already renders, with a Context Ontology Accelerator source and a Cedar policy" }
  - { name: "A live SQL tool", summary: "The agent queries the source; refused by ADR-004's reasoning" }
criteria:
  - "Freshness"
  - "Citation stability"
  - "Scope enforcement"
affects: [CAP-007, ABB-024, ABB-012]
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# CN-003 Live structured sources through a virtual knowledge graph

How should a table that lives in a database, rather than a file in the landing tree, be read in the ontology's terms?

| Option | Summary |
|---|---|
| Snapshots only | Export the table to a file and bind it; what exists |
| A virtual knowledge graph | Ontop over the R2RML the version already renders, with a Context Ontology Accelerator source and a Cedar policy |
| A live SQL tool | The agent queries the source; refused by ADR-004's reasoning |

Criteria: Freshness; Citation stability; Scope enforcement.

Status: resolved by ADR-009. Affects CAP-007, ABB-024, ABB-012.

The mapping already renders R2RML for this; nothing reads it yet. docs/architecture/aws/structured.md says where the accelerator fits.
