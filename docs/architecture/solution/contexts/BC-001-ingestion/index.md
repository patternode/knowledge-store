---
kind: bounded-context
id: BC-001
title: "BC-001 Ingestion"
description: "Sources, documents, passages and the lake's layers: getting content in, keeping one immutable copy, cutting it into citable units, and running the sweep that drives every other context."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
part_of: PL-001
contains: [ABB-001, ABB-002, ABB-003, ABB-004]
realises_capabilities: [CAP-002]
subdomain_kind: supporting
c4_levels: [container, component]
ubiquitous_language:
  - { term: "Source", definition: "A configured place content comes from: a type, options and a scope" }
  - { term: "Item", definition: "One thing a source offers, with a version the adapter uses to skip it next time" }
  - { term: "Document", definition: "One distinct piece of content, identified by the sha256 of its bytes; one bronze copy whatever its source keys" }
  - { term: "Passage", definition: "A deterministic chunk of a document, about 1,800 characters, with an id derived from the document and the chunk; the unit a citation points at" }
  - { term: "Landing, bronze, silver, gold", definition: "The lake's layers: uploads as they came, immutable copies, parsed text and passages, the record per ontology version" }
  - { term: "Collection", definition: "One corpus with its own ontology, sources and profile, under collections/<id>/" }
  - { term: "Sweep", definition: "One idempotent pass over every stage, under a lock, repeated until a round changes nothing" }
  - { term: "Scope", definition: "Public or private, stated on a source and carried on every document" }
relationships:
  - { with: BC-002, pattern: customer-supplier, role: downstream }
  - { with: BC-003, pattern: customer-supplier, role: upstream }
  - { with: BC-008, pattern: conformist, role: downstream }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# BC-001 Ingestion

| Property | Value |
|---|---|
| Context ID | BC-001 |
| Platform | PL-001 Knowledge Store |
| Owner team | Patternode (Dermot O'Brien) |
| Subdomain | supporting |
| Realises | CAP-002 |
| Contains | ABB-001, ABB-002, ABB-003, ABB-004 |

Sources, documents, passages and the lake's layers: getting content in, keeping one immutable copy, cutting it into citable units, and running the sweep that drives every other context.

## Ubiquitous language

| Term | Meaning in this context |
|---|---|
| Source | A configured place content comes from: a type, options and a scope |
| Item | One thing a source offers, with a version the adapter uses to skip it next time |
| Document | One distinct piece of content, identified by the sha256 of its bytes; one bronze copy whatever its source keys |
| Passage | A deterministic chunk of a document, about 1,800 characters, with an id derived from the document and the chunk; the unit a citation points at |
| Landing, bronze, silver, gold | The lake's layers: uploads as they came, immutable copies, parsed text and passages, the record per ontology version |
| Collection | One corpus with its own ontology, sources and profile, under collections/<id>/ |
| Sweep | One idempotent pass over every stage, under a lock, repeated until a round changes nothing |
| Scope | Public or private, stated on a source and carried on every document |

## Where the model lives today

- `adapters/ (the source adapter protocol and the three built-in adapters)`
- `pipeline/ingest.py, pipeline/refine.py, pipeline/run.py (the sweep, its lock, rounds and status)`
- `refine/ (parsers, HTML text, chunking)`
- `store.py, layout.py, collections.py, config.py (the lake port, its key layout, collections and their configuration)`

The sweep composes every stage in one process and calls into BC-002, BC-003 and BC-004 directly; the lake port (Store) is the one boundary every context shares. Terraform writes the collection configuration into the lake, so configuration is an input, not something this context owns.

## Relationships with other contexts

| With | Pattern | Role | Why |
|---|---|---|---|
| BC-002 | customer-supplier | downstream | The sweep calls the ontology context to discover, provide and publish |
| BC-003 | customer-supplier | upstream | Silver passages are what extraction reads |
| BC-008 | conformist | downstream | Uses the model client and configuration as given |

## Building blocks

ABB-001, ABB-002, ABB-003, ABB-004; each is a page under [../abbs](../../abbs/README.md).
