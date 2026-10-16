---
kind: use-case
id: UC-006
title: "UC-006 Map a table beside the documents"
description: "A curator maps a CSV, TSV or JSON table to the ontology's classes and attributes and publishes the mapping with the version, so that a question about a filter, a total or an exact value is answered from the table and cites the cell or the recomputed figure."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
primary_actor: "A curator"
secondary_actors: ["The sweep", "A reader asking a catalogue question"]
scenario: "S1 below"
preconditions:
  - "An ontology with the attributes the columns need"
  - "The mapping names only terms the ontology has"
success_criteria:
  - "A mapped file is bound at its content hash and skipped by refine and extract"
  - "A cited figure recomputes from the snapshot"
  - "A private table is invisible to a public caller"
frequency: low
supports_outcome: OC-001
realised_by_abbs: [ABB-008, ABB-010, ABB-012, ABB-015]
realised_by: [PAT-001, REF-001]
fulfilled_by_features: [FE-007]
model:
  diagram: components.drawio
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# UC-006 Map a table beside the documents

<!-- deck:cover subtitle="Map a table beside the documents" footnote="Use case, reversed from the implementation at 0.3.0. Draft." -->

| Field | Value |
|---|---|
| Use case | UC-006 |
| Consumer | A curator |
| Owner | Patternode (Dermot O'Brien) |
| Outcome | OC-001 |
| Rests on | The implementation as released; this use case is reversed from it |
| Realised by | PAT-001 Ontology-driven GraphRAG (logical) and REF-001 Knowledge Store on AWS (physical) |
| Fulfilled by | FE-007 |
| Date | 2026-10-16 |

## The solution in one sentence

A curator maps a CSV, TSV or JSON table to the ontology's classes and attributes and publishes the mapping with the version, so that a question about a filter, a total or an exact value is answered from the table and cites the cell or the recomputed figure.

A table parsed as prose loses its schema; a total cannot be quoted. The table needs to stay a table, bound at a snapshot, with its cells citable.

### What is different afterwards

Catalogue questions are answered from rows and figures, each citation opening the row with the cell highlighted; a metric is recomputed before it is shown.

## Diagram

The diagram is generated from the two tables below with the pattern skill's model tool (`model emit index.md components.drawio`, then `model render`); it is not yet emitted.

## Participants

| Participant | Role in this use case | Kind |
|---|---|---|
| 01 Curator | Writes mappings.yaml and metrics.osi.yaml | actor |
| 02 Ontology store | The mapping published and rendered with the version | solution |
| 03 Sweep | Binds the snapshot into gold | solution |
| 04 Structured tools | describe, lookup_rows, aggregate | solution |
| 05 Reader | Asks a catalogue question | actor |

## Interactions

| Interface | Provider | Consumer | Purpose |
|---|---|---|---|
| IF-01 | 02 Ontology store | 01 Curator | publish with the mapping; refused on an unknown term |
| IF-02 | 03 Sweep | 02 Ontology store | read the structured rendition |
| IF-03 | 04 Structured tools | 03 Sweep | cells and rows from the snapshot |
| IF-04 | 04 Structured tools | 05 Reader | through the agent: a cell or a figure cited |

## Scenarios

### S1 Main success scenario

| Step | Actor | Target | Action | Interface |
|---|---|---|---|---|
| 1 | 01 Curator | 02 Ontology store | write the mapping in the ontology's terms; publish the version | IF-01 |
| 2 | 03 Sweep | 02 Ontology store | read structured/mapping.json | IF-02 |
| 3 | 03 Sweep | 04 Structured tools | bind the file: rows as entities keyed by the key columns, values as cells with the snapshot hash; validate with SHACL | IF-03 |
| 4 | 05 Reader | 04 Structured tools | ask a catalogue question; the agent looks up rows or aggregates | IF-04 |
| 5 | 04 Structured tools | 05 Reader | the claim cites the cell or the figure; the check recomputes it | IF-04 |

## Data

- The mapping and metrics, the binding record, the cells file

## Measures

- Catalogue questions answered correctly in the evaluation set

## Preconditions and success

Preconditions: An ontology with the attributes the columns need; The mapping names only terms the ontology has.

Success: A mapped file is bound at its content hash and skipped by refine and extract; A cited figure recomputes from the snapshot; A private table is invisible to a public caller.
