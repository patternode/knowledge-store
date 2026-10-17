---
kind: abb
id: ABB-009
title: "ABB-009 Ontology-guided extraction"
short_name: "EXTR"
description: "Extraction of typed facts from a document by a forced tool call whose schema is the ontology, with every fact checked for grounding in its passages and against SHACL, repaired or dropped item by item, written as a named graph with provenance, and extended by delta extraction when the ontology grows."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Extraction"
part_of: BC-003
realises_capabilities: [CAP-004]
realised_by: [SBB-014, SBB-012]
requires:
  - { abb: ABB-006, cardinality: "1", rationale: "The version's tool schema and shapes" }
  - { abb: ABB-003, cardinality: "1", rationale: "Silver passages" }
  - { abb: ABB-022, cardinality: "1", rationale: "Model calls, priced" }
domains: [application, data]
interfaces:
  - { id: "I1", direction: "in", type: "query", description: "A silver document and its passages; the active version; known entities for a delta" }
  - { id: "I2", direction: "out", type: "query", description: "A named graph of assertions with provenance; the extraction record; candidates; rejections" }
  - { id: "I3", direction: "in", type: "query", description: "The extraction tool schema generated from the ontology" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/extract/schema.py, extractor.py, validate.py, rdf.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-009 Ontology-guided extraction

| Property | Value |
|---|---|
| ABB ID | ABB-009 |
| ABB Name | Ontology-guided extraction |
| Short Name | EXTR |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Extraction |
| Bounded context | BC-003 |
| Realises | CAP-004 |
| Realised by | SBB-014, SBB-012 |

Extraction of typed facts from a document by a forced tool call whose schema is the ontology, with every fact checked for grounding in its passages and against SHACL, repaired or dropped item by item, written as a named graph with provenance, and extended by delta extraction when the ontology grows.

## 1  Purpose

The model must answer in the ontology's terms and prove each fact from the text. The tool schema forces the first; the grounding and shape checks enforce the second; provenance makes every assertion auditable.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Tool schema.** record_knowledge generated from the version: entities, attributes, relations, candidates
- **Extractor loop.** Converse with throttle retry; up to two repairs; salvage of what passed
- **Checks.** Shape, ontology, grounding (names and values in cited passages), SHACL with inference
- **RDF builder.** Content-derived IRIs; reified assertions with extractedFrom, extractedBy; N-Quads
- **Delta.** Selection by candidate, lexical match or retype; new terms only; ks:delta

### 2.3  Attributes

- **Provenance.** Run, model, prompt version, ontology version on every assertion
- **Concurrency.** A worker pool per sweep
- **Cost bound.** One pass per document per full version; deltas over selected documents

### 2.4  Semantic

Inside: extraction of one document. Outside: the sweep that selects documents, the projection that reads the result.

### 2.5  Identity & Access Management

The pipeline task invokes the extraction model only; no document leaves the account except to the model in the account's region, or to the Anthropic API when chosen.

### 2.6  Observability

An extraction record per document with status, run and usage; the ledger prices every call.

### 2.7  Governance & Policy Enforcement

Prompt version strings; a rejected document is kept with its reasons; candidates never enter the graph.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | data | A silver document and its passages; the active version; known entities for a delta |
| I2 | out | data | A named graph of assertions with provenance; the extraction record; candidates; rejections |
| I3 | in | schema | The extraction tool schema generated from the ontology |

### 3.4  Capability dependencies (requires)

- ABB-006 (1): The version's tool schema and shapes
- ABB-003 (1): Silver passages
- ABB-022 (1): Model calls, priced

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/extract/schema.py, extractor.py, validate.py, rdf.py; pipeline/extract.py` |
| Capabilities | CAP-004 |
| Context | BC-003 |

## 5  Solution Building Block guidance

Realised in the pipeline image with Claude; the schema generation is the thing a different model would need to honour.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
