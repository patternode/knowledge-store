---
kind: bounded-context
id: BC-002
title: "BC-002 Ontology"
description: "Terms, versions, renditions, drafts, candidates and mappings: what a collection's documents are about, owned by a person and released in classified versions."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
part_of: PL-001
contains: [ABB-006]
realises_capabilities: [CAP-003, CAP-007]
subdomain_kind: core
c4_levels: [container, component]
ubiquitous_language:
  - { term: "Master", definition: "The curated OWL Turtle file a person edits; the only thing people edit" }
  - { term: "Rendition", definition: "A derived form a consumer reads: for the agent, extraction, Neo4j, AGE, JSON-LD, R2RML" }
  - { term: "Version", definition: "An immutable publication of the master, with a manifest of checksums; semver; chains to a base" }
  - { term: "Change kind", definition: "descriptive, additive, semantic or removal: what the diff found, which decides the bump and the re-extraction" }
  - { term: "Draft", definition: "A proposed master in ontology/drafts, from discovery or a revision, for a person to curate" }
  - { term: "Candidate", definition: "A term extraction could not place, with its documents and evidence, kept out of the graph" }
  - { term: "Request", definition: "A workbench gap report a curator kept, merged into the candidate register as asked terms" }
  - { term: "Core vocabulary", definition: "ks:, the provenance terms every deployment shares and code may name; a domain term is never named by code" }
  - { term: "Mapping", definition: "Which table fills which class, with key, columns and scope; published with the version; immutable once published" }
relationships:
  - { with: BC-003, pattern: published-language, role: upstream }
  - { with: BC-004, pattern: published-language, role: upstream }
  - { with: BC-005, pattern: published-language, role: upstream }
  - { with: BC-005, pattern: customer-supplier, role: downstream }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# BC-002 Ontology

| Property | Value |
|---|---|
| Context ID | BC-002 |
| Platform | PL-001 Knowledge Store |
| Owner team | Patternode (Dermot O'Brien) |
| Subdomain | core |
| Realises | CAP-003, CAP-007 |
| Contains | ABB-006 |

Terms, versions, renditions, drafts, candidates and mappings: what a collection's documents are about, owned by a person and released in classified versions.

## Ubiquitous language

| Term | Meaning in this context |
|---|---|
| Master | The curated OWL Turtle file a person edits; the only thing people edit |
| Rendition | A derived form a consumer reads: for the agent, extraction, Neo4j, AGE, JSON-LD, R2RML |
| Version | An immutable publication of the master, with a manifest of checksums; semver; chains to a base |
| Change kind | descriptive, additive, semantic or removal: what the diff found, which decides the bump and the re-extraction |
| Draft | A proposed master in ontology/drafts, from discovery or a revision, for a person to curate |
| Candidate | A term extraction could not place, with its documents and evidence, kept out of the graph |
| Request | A workbench gap report a curator kept, merged into the candidate register as asked terms |
| Core vocabulary | ks:, the provenance terms every deployment shares and code may name; a domain term is never named by code |
| Mapping | Which table fills which class, with key, columns and scope; published with the version; immutable once published |

## Where the model lives today

- `ontology/model.py, writer.py (the spec loaded from Turtle; Turtle and SHACL written from a definition)`
- `ontology/discover.py, review.py (a first draft from a sample, reviewed)`
- `ontology/versions.py, renditions.py, provided.py (publish, classify, chain, activate, render; the provided master)`
- `ontology/candidates.py (the register and the revision proposal)`
- `structured/mapping.py (the table mapping and metrics as part of a version; R2RML)`
- `ontology/core.ttl, core-shapes.ttl (the core vocabulary ks:)`

Discovery and review are LLM calls whose edits are applied in code. Publish refuses an understated bump and an existing version. Candidates reads the workbench module directly for requests, a dependency that runs against the layering and belongs behind the request file format.

## Relationships with other contexts

| With | Pattern | Role | Why |
|---|---|---|---|
| BC-003 | published-language | upstream | Extraction reads the version's tool schema and shapes, never the master |
| BC-004 | published-language | upstream | The graph stores read the Neo4j and AGE renditions and the T-Box |
| BC-005 | published-language | upstream | The agent reads the agent rendition and the mapping lines |
| BC-005 | customer-supplier | downstream | Ontology requests from the workbench feed the candidate register |

## Building blocks

ABB-006; each is a page under [../abbs](../../abbs/README.md). Each is one C4 container; what runs inside it is listed on its page.
