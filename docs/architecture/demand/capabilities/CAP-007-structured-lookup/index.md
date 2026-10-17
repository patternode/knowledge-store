---
kind: capability
id: CAP-007
title: "CAP-007 Structured lookup"
description: "Keeping a mapped table beside the documents in the ontology's own terms, so a question can filter, total or match a cell and the answer cites the cell or the recomputed figure."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
level: L2
parent: CAP-001
components:
  organisation: "The curator writes the mapping and metrics beside the ontology master"
  people: ["Curators", "Analysts asking catalogue questions"]
  processes:
    - "Write mappings.yaml and metrics.osi.yaml; publish refuses a term the ontology lacks"
    - "Bind each mapped CSV, TSV or JSON array as a snapshot with rows as entities and values as cells"
    - "Describe tables, look up rows, aggregate with a parsed read-only SELECT"
    - "Cite a cell or a figure; recompute it at check time"
  technology: "mappings.yaml and the OSI metrics file, R2RML rendered per version, snapshots in gold as N-Quads and cells, canonical values, fixed structured tools"
maturity:
  current: 3
  target: 4
  assessment_date: 2026-10-16
  assessor: "Patternode (Dermot O'Brien), reversed from the implementation"
subdomain_kind: core
provided_by_platform: PL-001
realised_by_abbs: [ABB-024, ABB-012]
gaps:
  - "Only files in the landing tree are bound; a live source through Context Ontology Accelerator is designed, not wired (CN-003)"
  - "The SQL of a metric is parsed and recomputed, never executed"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# CAP-007 Structured lookup

| Property | Value |
|---|---|
| Capability ID | CAP-007 |
| Level | L2 |
| Parent | CAP-001 |
| Status | Draft, reversed from the implementation at 0.3.0 |
| Subdomain | core |
| Maturity | 3, target 4 |
| Realised by | ABB-024, ABB-012 |

Keeping a mapped table beside the documents in the ontology's own terms, so a question can filter, total or match a cell and the answer cites the cell or the recomputed figure.

## 1  Purpose

A table that is the source cannot be grounded as a quote from prose. A mapping published with the ontology version says which table fills which class; the sweep binds the file at its snapshot; a cell or a figure is a citation that code checks against the snapshot.

## 2  Capability definition

| Dimension | For Knowledge Store |
|---|---|
| Organisation | The curator writes the mapping and metrics beside the ontology master |
| People | Curators, Analysts asking catalogue questions |
| Processes | Write mappings.yaml and metrics.osi.yaml; publish refuses a term the ontology lacks; Bind each mapped CSV, TSV or JSON array as a snapshot with rows as entities and values as cells; Describe tables, look up rows, aggregate with a parsed read-only SELECT; Cite a cell or a figure; recompute it at check time |
| Technology | mappings.yaml and the OSI metrics file, R2RML rendered per version, snapshots in gold as N-Quads and cells, canonical values, fixed structured tools |

## 3  Sub-capabilities

| Sub-capability | What it covers | Status |
|---|---|---|
| Mapping as part of the version | Checked at publish, rendered as JSON and R2RML | In place |
| Binding | Snapshot into gold with cells | In place |
| Lookup and aggregate | Fixed tools over the snapshot | In place |
| Live sources | A table in place through a virtual knowledge graph | Not started |

## 4  What the implementation does today

The space-missions example carries two catalogue CSVs beside its documents; five catalogue questions are added to the prompt when the mapping supports them; a cell citation shows the whole row; metrics and ad hoc figures have ids that name their computation and snapshot.

## 5  Maturity

Current maturity is 3 on the 0 to 5 scale, read from the implementation: the capability is defined, built and in service in the Patternode lab and in any deployment of the module. Target 4.

## 6  Gaps

- Only files in the landing tree are bound; a live source through Context Ontology Accelerator is designed, not wired (CN-003)
- The SQL of a metric is parsed and recomputed, never executed
