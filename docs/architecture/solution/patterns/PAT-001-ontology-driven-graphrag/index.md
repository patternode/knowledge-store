---
kind: pattern
id: PAT-001
title: "PAT-001 Ontology-driven GraphRAG with grounded answers"
pattern_type: architecture-pattern
pattern_scope: platform
status: draft
version: "0.2"
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
author: "Patternode (Dermot O'Brien)"
realises: [CAP-003, CAP-004, CAP-005, CAP-006, CAP-007, CAP-008, CAP-009]
serves: [UC-001, UC-002, UC-003, UC-004, UC-005, UC-006, UC-007, UC-008]
implemented_by: [REF-001]
model:
  diagram: components.drawio
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# PAT-001 Ontology-driven GraphRAG with grounded answers

<!-- deck:cover subtitle="The logical pattern: ontology, extraction with provenance, the graph as record, grounded answering" footnote="Reversed from the implementation at 0.3.0. Draft." -->

The logical pattern: technology-agnostic, in architecture building blocks, each one C4 container per the building block calibration standard. REF-001 is its physical form on AWS. Every use case in [../../demand/use-cases](../../../demand/use-cases/README.md) is realised by this pattern, and its scenarios walk theirs across the blocks named here; in UML terms this document is the use-case realization and the pattern it applies, in one.

<!-- deck:slide label="Context" -->

## Context

An organisation has documents and wants to answer questions from them with every statement checkable. Retrieval over chunks answers fluently and unverifiably; a graph answers precisely but only in the terms someone defined. The pattern joins the two under an ontology a person owns: documents become passages, passages become typed facts that cite them, the facts are the record, projections serve queries, and an agent answers through fixed tools with claims that code checks before anything is shown.

The audience is a team building a knowledge store over its own documents, in any domain, who will own the ontology.

<!-- deck:slide label="Non-goals" -->

### Non-goals

- A general chat assistant: the agent answers from the collection or abstains.
- A model as judge of truth: every check is code, with the guardrail as a second, bounded opinion.
- Free querying by the model: the tools are fixed.
- A document management system: sources are read, never managed.

<!-- deck:slide label="Quality attributes" -->

### Quality attributes

| Quality attribute | Scenario | Response measure |
|---|---|---|
| Groundedness | A model proposes a claim whose quote is not in the passage | The claim is repaired once or removed; it never reaches the page |
| Scope safety | A public caller's model asks a tool for private content | The interceptor sets the scope; the tool returns public content only |
| Cost | A question runs away in tool calls | The hook cancels the seventeenth call; the agent answers from what it has |
| Rebuildability | A projection is lost | The next sweep rebuilds it from gold; the pointer moves when counts check |
| Governance | A term is proposed from a document | It stays a candidate until a person publishes a version containing it |

<!-- deck:slide label="Component view" -->

## Diagram

![PAT-001 building blocks and interfaces](./components.svg)

Generated from the Required Building Blocks and Interfaces tables with the model skill (`components.drawio` is the source); the as-built picture is REF-001's.

<!-- deck:slide label="Building blocks" -->

## Required Building Blocks

Every block is one container. What runs inside each, such as the adapters, refinement, extraction and binding inside the sweep, or the checks, valves and recorder inside the agent, is on the block's page and is not a block here.

| Building Block | Role in the pattern |
|---|---|
| ABB-002 Lake and layering | The record and its layers, the pointers, the lock and the ledger; the contract every block reads |
| ABB-004 Pipeline sweep | The idempotent pass that converges the store: items and bytes in, passages, drafts, typed facts, snapshots and candidates out, projections loaded |
| ABB-006 Ontology publisher | Immutable classified versions with their renditions and mapping, published and activated by a person |
| ABB-011 Knowledge graph store | Gold as named graphs the tools query; the optional backends behind the same port |
| ABB-013 Passage index | One vector per passage; the hit is a passage id |
| ABB-012 Tool gateway and fixed query tools | Read-only tools in the ontology's terms, offered through a gateway that sets the caller's scope on every call |
| ABB-014 Answering agent | Plans in the ontology's terms, proposes claims, checks every citation and claim, runs under its valves, records its steps |
| ABB-019 Chat API | The narrow door: admission, the quota, dispatch, state and signed links |
| ABB-018 Chat page | Where grounding is visible |
| ABB-020 Identity | The person all the way down: sign-in, tokens, the scope rule |
| ABB-021 Evaluation runner and scorer | Right, not only grounded |

<!-- deck:slide label="Interfaces" -->

## Interfaces

| Interface | Provider | Consumer | Purpose |
|---|---|---|---|
| IF-01 | ABB-002 Lake and layering | ABB-004 Pipeline sweep | the lake port and layout: landing, bronze, silver, gold, the active version |
| IF-02 | ABB-004 Pipeline sweep | ABB-002 Lake and layering | bronze, silver, gold, drafts, candidates, the index, status and the ledger |
| IF-03 | ABB-006 Ontology publisher | ABB-002 Lake and layering | an immutable version, its renditions and manifest, the active pointer |
| IF-04 | ABB-002 Lake and layering | ABB-006 Ontology publisher | the active version, the drafts and the candidate register to diff and propose from |
| IF-05 | ABB-004 Pipeline sweep | ABB-011 Knowledge graph store | named graphs loaded per document per version; pointers moved when counts check |
| IF-06 | ABB-004 Pipeline sweep | ABB-013 Passage index | passages synced, one vector each; an ingestion job per change |
| IF-07 | ABB-011 Knowledge graph store | ABB-012 Tool gateway and fixed query tools | fixed read-only queries in the ontology's terms |
| IF-08 | ABB-013 Passage index | ABB-012 Tool gateway and fixed query tools | passages by meaning, filtered to the collection and the caller's scope |
| IF-09 | ABB-002 Lake and layering | ABB-012 Tool gateway and fixed query tools | silver, the index, snapshots and cells |
| IF-10 | ABB-012 Tool gateway and fixed query tools | ABB-014 Answering agent | fixed tools as the caller, the scope set by the interceptor |
| IF-11 | ABB-014 Answering agent | ABB-019 Chat API | the answer as checked claims, steps streamed |
| IF-12 | ABB-019 Chat API | ABB-018 Chat page | the HTTP API |
| IF-13 | ABB-020 Identity | ABB-018 Chat page | sign-in and tokens |
| IF-14 | ABB-020 Identity | ABB-019 Chat API | who is asking, from the verified token |
| IF-15 | ABB-020 Identity | ABB-012 Tool gateway and fixed query tools | the token the gateway verifies and reads scope from |
| IF-16 | ABB-020 Identity | ABB-014 Answering agent | the caller's token, presented onward to the tools |
| IF-17 | ABB-021 Evaluation runner and scorer | ABB-014 Answering agent | evaluation questions, in process or as a person through the API |
| IF-18 | ABB-002 Lake and layering | ABB-019 Chat API | documents and tables to link after the scope check; requests written |

## Scenarios

The scenarios are the use cases': UC-001 S1 to S3 for answering, UC-002 for the sweep, UC-003 to UC-005 for the ontology lifecycle, UC-006 for tables, UC-007 for evaluation, UC-008 for scope. Each step of each is a call across one of the interfaces above.

<!-- deck:slide label="Controls" -->

## Controls

| Control | Where | What it stops |
|---|---|---|
| The scope rule at every hop | ABB-020, applied by ABB-012, ABB-019 and ABB-014 | A public caller reading private content |
| Claims checked by code | ABB-014 | An invented quote, value or figure |
| Fixed tools | ABB-012 | Writes, free queries, escape from scope |
| Valves | ABB-014 per question; ABB-019 per person per day | Runaway cost per question, per person, per deployment |
| Publish refuses an understated bump | ABB-006 | A silent semantic change |
| Candidates stay out of the graph | ABB-004 | Document text changing the ontology |
| Documents as data | ABB-004 | Document text being executed or trusted |

<!-- deck:slide label="Decisions" -->

## Decisions

ADR-001 to ADR-005 and ADR-010 are this pattern's; ADR-006 to ADR-009 belong to REF-001.
