---
kind: capability
id: CAP-004
title: "CAP-004 Fact extraction with provenance"
description: "Extracting typed facts from passages against the active ontology version, with every fact grounded in the passages it cites and validated by SHACL, kept per document per version as the record, and extended by delta extraction when the ontology grows."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
level: L2
parent: CAP-001
components:
  organisation: "Runs inside the sweep; the curator decides when a full re-extraction is budgeted"
  people: ["Curators (versions decide the cost)", "Administrators (model and workers)"]
  processes:
    - "Extract each silver document against the active version with a forced tool call whose schema comes from the ontology"
    - "Check grounding and SHACL; repair up to twice; salvage"
    - "Write the named graph, the extraction record, candidates and rejections"
    - "Select documents for a delta after an additive version; re-extract all after a major one"
    - "Bind mapped tables as snapshots with cells"
  technology: "A tool schema generated from the ontology, the Converse model client, rdflib and pySHACL, N-Quads per document, canonical values"
maturity:
  current: 4
  target: 4
  assessment_date: 2026-10-16
  assessor: "Patternode (Dermot O'Brien), reversed from the implementation"
subdomain_kind: core
provided_by_platform: PL-001
realised_by_abbs: [ABB-024]
gaps:
  - "Delta selection is a heuristic; a new term can apply to a document it misses (extract --all-delta exists)"
  - "A periodic full re-extraction is advised and not scheduled"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# CAP-004 Fact extraction with provenance

| Property | Value |
|---|---|
| Capability ID | CAP-004 |
| Level | L2 |
| Parent | CAP-001 |
| Status | Draft, reversed from the implementation at 0.3.0 |
| Subdomain | core |
| Maturity | 4, target 4 |
| Realised by | ABB-024 |

Extracting typed facts from passages against the active ontology version, with every fact grounded in the passages it cites and validated by SHACL, kept per document per version as the record, and extended by delta extraction when the ontology grows.

## 1  Purpose

A fact without its passage is an opinion of the model. Extraction produces assertions that name the passages they were stated in and the run that produced them, checks names and values appear in those passages, validates shapes, repairs or drops item by item, and records what it could not place as candidates.

## 2  Capability definition

| Dimension | For Knowledge Store |
|---|---|
| Organisation | Runs inside the sweep; the curator decides when a full re-extraction is budgeted |
| People | Curators (versions decide the cost), Administrators (model and workers) |
| Processes | Extract each silver document against the active version with a forced tool call whose schema comes from the ontology; Check grounding and SHACL; repair up to twice; salvage; Write the named graph, the extraction record, candidates and rejections; Select documents for a delta after an additive version; re-extract all after a major one; Bind mapped tables as snapshots with cells |
| Technology | A tool schema generated from the ontology, the Converse model client, rdflib and pySHACL, N-Quads per document, canonical values |

## 3  Sub-capabilities

| Sub-capability | What it covers | Status |
|---|---|---|
| Ontology-guided extraction | Forced tool call against the version's schema | In place |
| Fact grounding | Names and values must appear in the cited passages | In place |
| Shape validation | Core and version SHACL with rdfs inference | In place |
| Provenance | Run, model, prompt version and ontology version on every assertion | In place |
| Delta extraction | New terms only, for selected documents | In place |
| Table binding | Snapshots into gold with cells for citation | In place |

## 4  What the implementation does today

One named graph per document per version, assertions reified with ks:extractedFrom and ks:extractedBy, entity IRIs derived from content, candidates kept only when their evidence is verbatim in a cited passage. Tables named by the mapping are bound rather than extracted: rows become entities keyed by the key columns, values become cells with the snapshot hash, so a figure can be cited and recomputed.

## 5  Maturity

Current maturity is 4 on the 0 to 5 scale, read from the implementation: the capability is defined, built and in service in the Patternode lab and in any deployment of the module. Target 4.

## 6  Gaps

- Delta selection is a heuristic; a new term can apply to a document it misses (extract --all-delta exists)
- A periodic full re-extraction is advised and not scheduled
