---
kind: abb
id: ABB-005
title: "ABB-005 Ontology discovery and review"
short_name: "DISC"
description: "A first ontology proposed from a sample of the documents, consolidated, reviewed by a second model pass whose edits are applied in code, and written as a draft for a person."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Ontology"
part_of: BC-002
realises_capabilities: [CAP-003]
realised_by: [SBB-014, SBB-012]
requires:
  - { abb: ABB-003, cardinality: "1", rationale: "Samples silver passages" }
  - { abb: ABB-022, cardinality: "1", rationale: "Every proposal is a model call" }
domains: [application, business]
interfaces:
  - { id: "I1", direction: "in", type: "query", description: "A sample of refined documents, the profile" }
  - { id: "I2", direction: "out", type: "query", description: "A draft: ontology.ttl, shapes.ttl, report.json with support, stability, rejections and the review's edits" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/ontology/discover.py, review.py, writer.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-005 Ontology discovery and review

| Property | Value |
|---|---|
| ABB ID | ABB-005 |
| ABB Name | Ontology discovery and review |
| Short Name | DISC |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Ontology |
| Bounded context | BC-002 |
| Realises | CAP-003 |
| Realised by | SBB-014, SBB-012 |

A first ontology proposed from a sample of the documents, consolidated, reviewed by a second model pass whose edits are applied in code, and written as a draft for a person.

## 1  Purpose

A collection with no ontology needs a starting point that is small, grounded in its documents and honest about its variance. Extract, define, canonicalise gives that; review catches the obvious faults; a person does the rest.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Sampling.** Round robin across sources, seeded, up to twenty documents twice, eight passages each
- **Proposal.** Per document: classes, relations, attributes with definitions and verbatim examples
- **Aggregation.** By normalised name, with document counts, stability and Jaccard overlap
- **Consolidation.** One call to about fifteen classes with hierarchy, domains, ranges, datatypes, and what was rejected
- **Review.** Edits only: parent, merge, drop, domain, range, datatype; cycles and unknown terms skipped
- **Writer.** Turtle with evidence comments and generated SHACL

### 2.3  Attributes

- **Grounding.** An example not in its passage is dropped
- **Reproducibility.** Seeded sampling and a prompt version string
- **Cost bound.** Sample times resamples, whatever the collection size

### 2.4  Semantic

Inside: proposing and reviewing a draft. Outside: publishing it (ABB-006) and growing it (ABB-007).

### 2.5  Identity & Access Management

The pipeline task invokes the extraction model; a draft can quote private documents, so drafts are served to private readers only.

### 2.6  Observability

The report records every proposal, edit and skip; the status shows awaiting curation.

### 2.7  Governance & Policy Enforcement

Curated mode by default: nothing is published without a person. Auto mode publishes 0.1.0 provisionally and says so.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | data | A sample of refined documents, the profile |
| I2 | out | artefact | A draft: ontology.ttl, shapes.ttl, report.json with support, stability, rejections and the review's edits |

### 3.4  Capability dependencies (requires)

- ABB-003 (1): Samples silver passages
- ABB-022 (1): Every proposal is a model call

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/ontology/discover.py, review.py, writer.py` |
| Capabilities | CAP-003 |
| Context | BC-002 |

## 5  Solution Building Block guidance

Realised in the pipeline image with Claude through the model client.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
