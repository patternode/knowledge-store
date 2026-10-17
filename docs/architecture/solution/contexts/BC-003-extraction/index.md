---
kind: bounded-context
id: BC-003
title: "BC-003 Extraction"
description: "Extraction runs, assertions, grounding of facts, SHACL validation, table snapshots and cells: turning passages and rows into typed facts that cite where they came from, and refusing those that do not."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
part_of: PL-001
contains: [ABB-024]
realises_capabilities: [CAP-004, CAP-007]
subdomain_kind: core
c4_levels: [container, component]
ubiquitous_language:
  - { term: "Extraction run", definition: "One pass of a model over a document against one ontology version, with model id, prompt version and whether it was a delta" }
  - { term: "Assertion", definition: "A reified fact: subject, predicate, object, the passages or cells it is stated in, the run that recorded it" }
  - { term: "Grounding (of a fact)", definition: "The names and values of a fact appear verbatim in the passages it cites; otherwise repaired or dropped" }
  - { term: "Candidate", definition: "A term the schema had no place for, kept with its evidence when the evidence is in the passage" }
  - { term: "Delta", definition: "An extraction of only the terms an additive version added, over the documents selected for it" }
  - { term: "Snapshot", definition: "A mapped table at one content hash, bound into gold as rows and cells" }
  - { term: "Cell", definition: "One column of one row of one snapshot: the unit a table fact cites" }
  - { term: "Entity IRI", definition: "Derived from content: the class plus the normalised label for extracted entities, the class plus the key columns for rows" }
relationships:
  - { with: BC-002, pattern: published-language, role: downstream }
  - { with: BC-004, pattern: customer-supplier, role: upstream }
  - { with: BC-008, pattern: conformist, role: downstream }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# BC-003 Extraction

| Property | Value |
|---|---|
| Context ID | BC-003 |
| Platform | PL-001 Knowledge Store |
| Owner team | Patternode (Dermot O'Brien) |
| Subdomain | core |
| Realises | CAP-004, CAP-007 |
| Contains | ABB-024 |

Extraction runs, assertions, grounding of facts, SHACL validation, table snapshots and cells: turning passages and rows into typed facts that cite where they came from, and refusing those that do not.

## Ubiquitous language

| Term | Meaning in this context |
|---|---|
| Extraction run | One pass of a model over a document against one ontology version, with model id, prompt version and whether it was a delta |
| Assertion | A reified fact: subject, predicate, object, the passages or cells it is stated in, the run that recorded it |
| Grounding (of a fact) | The names and values of a fact appear verbatim in the passages it cites; otherwise repaired or dropped |
| Candidate | A term the schema had no place for, kept with its evidence when the evidence is in the passage |
| Delta | An extraction of only the terms an additive version added, over the documents selected for it |
| Snapshot | A mapped table at one content hash, bound into gold as rows and cells |
| Cell | One column of one row of one snapshot: the unit a table fact cites |
| Entity IRI | Derived from content: the class plus the normalised label for extracted entities, the class plus the key columns for rows |

## Where the model lives today

- `extract/schema.py, extractor.py, validate.py, rdf.py (the tool schema from the ontology, the per-document loop, the checks, the RDF with provenance)`
- `pipeline/extract.py (full and delta extraction over silver)`
- `structured/bind.py (snapshots into gold with cells)`
- `values.py (one canonical form for literals), claims.py is not here: scope is BC-006's rule`

One named graph per document per version; two repairs then salvage; pySHACL with rdfs inference under a parser lock. Bind keeps its own copy of the version chain so a tool Lambda can walk it without the ontology parser, a small duplication that marks where the context boundary falls.

## Relationships with other contexts

| With | Pattern | Role | Why |
|---|---|---|---|
| BC-002 | published-language | downstream | Reads the version's schema, shapes and mapping rendition |
| BC-004 | customer-supplier | upstream | Gold per document per version is what projection and loading read |
| BC-008 | conformist | downstream | The model client and the ledger as given |

## Building blocks

This context has no container of its own: ontology-guided extraction and table binding run as components of ABB-024 Ingestion and extraction pipeline, which BC-001 owns (CN-006). The first pass's ABB-009 and ABB-010 are rows in its document, retired under the [calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md).
