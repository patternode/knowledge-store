---
kind: pattern
id: PAT-001
title: "PAT-001 Ontology-driven GraphRAG with grounded answers"
pattern_type: architecture-pattern
pattern_scope: platform
status: draft
version: "0.1"
created: 2026-10-16
last_modified: 2026-10-16
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

The logical pattern: technology-agnostic, in architecture building blocks. REF-001 is its physical form on AWS. Every use case in [../../demand/use-cases](../../../demand/use-cases/README.md) is realised by this pattern, and its scenarios walk theirs across the blocks named here; in UML terms this document is the use-case realization and the pattern it applies, in one.

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

| Building Block | Role in the pattern |
|---|---|
| ABB-001 Source adapters | Items and bytes from each configured source |
| ABB-002 Lake and layering | The record and its layers; the contract every block reads |
| ABB-003 Document refinement | Passages, the unit of citation |
| ABB-004 Sweep orchestration | The idempotent pass that converges the store |
| ABB-005 Ontology discovery and review | A first draft from the documents |
| ABB-006 Ontology versioning and renditions | Immutable classified versions; renditions for every consumer |
| ABB-007 Candidate register and revision proposal | Growth from demand, through a person |
| ABB-008 Table mapping definition | Tables in the ontology's terms, published with the version |
| ABB-009 Ontology-guided extraction | Typed facts that cite their passages, validated by shapes |
| ABB-010 Table binding | Snapshots with citable cells |
| ABB-011 Graph record and projection | Gold as the record; projections with pointers |
| ABB-012 Fixed query tools | Read-only tools in the ontology's terms, scope-filtered |
| ABB-013 Passage search by meaning | One vector per passage; the hit is a passage id |
| ABB-014 Answering agent | Plans in the ontology's terms; proposes claims |
| ABB-015 Claim grounding and checks | Nothing shown unchecked |
| ABB-016 Valves and quotas | Every limit, where it bites |
| ABB-017 Workbench | Steps, cost, term usage, requests |
| ABB-018 Chat page | Where grounding is visible |
| ABB-019 Chat API | The narrow door |
| ABB-020 Identity and scope | The person all the way down |
| ABB-021 Evaluation runner and scorer | Right, not only grounded |
| ABB-022 Model access and ledger | One client, every call priced |

<!-- deck:slide label="Interfaces" -->

## Interfaces

| Interface | Provider | Consumer | Purpose |
|---|---|---|---|
| IF-01 | ABB-002 Lake and layering | ABB-004 Sweep orchestration | the lake port and layout |
| IF-02 | ABB-001 Source adapters | ABB-004 Sweep orchestration | items and bytes from each source |
| IF-03 | ABB-003 Document refinement | ABB-009 Ontology-guided extraction | silver passages |
| IF-04 | ABB-005 Ontology discovery and review | ABB-006 Ontology versioning and renditions | a draft to publish |
| IF-05 | ABB-006 Ontology versioning and renditions | ABB-009 Ontology-guided extraction | the tool schema and shapes of the active version |
| IF-06 | ABB-006 Ontology versioning and renditions | ABB-014 Answering agent | the agent rendition |
| IF-07 | ABB-006 Ontology versioning and renditions | ABB-011 Graph record and projection | the store renditions and the T-Box |
| IF-08 | ABB-008 Table mapping definition | ABB-010 Table binding | the structured mapping rendition |
| IF-09 | ABB-009 Ontology-guided extraction | ABB-011 Graph record and projection | gold per document per version |
| IF-10 | ABB-010 Table binding | ABB-012 Fixed query tools | snapshots, cells and figures |
| IF-11 | ABB-011 Graph record and projection | ABB-012 Fixed query tools | the projections to query |
| IF-12 | ABB-003 Document refinement | ABB-013 Passage search by meaning | passages to index and read |
| IF-13 | ABB-012 Fixed query tools | ABB-014 Answering agent | fixed tools as the caller |
| IF-14 | ABB-013 Passage search by meaning | ABB-014 Answering agent | passage search and read |
| IF-15 | ABB-014 Answering agent | ABB-015 Claim grounding and checks | proposed claims; repairs back |
| IF-16 | ABB-016 Valves and quotas | ABB-014 Answering agent | limits on every call |
| IF-17 | ABB-014 Answering agent | ABB-017 Workbench | steps, usage, gap reports |
| IF-18 | ABB-017 Workbench | ABB-007 Candidate register and revision proposal | ontology requests |
| IF-19 | ABB-009 Ontology-guided extraction | ABB-007 Candidate register and revision proposal | candidates |
| IF-20 | ABB-007 Candidate register and revision proposal | ABB-006 Ontology versioning and renditions | a revision draft |
| IF-21 | ABB-014 Answering agent | ABB-019 Chat API | the answer, steps streamed |
| IF-22 | ABB-019 Chat API | ABB-018 Chat page | the HTTP API |
| IF-23 | ABB-020 Identity and scope | ABB-019 Chat API | who is asking |
| IF-24 | ABB-020 Identity and scope | ABB-012 Fixed query tools | the caller's scope on every call |
| IF-25 | ABB-022 Model access and ledger | ABB-009 Ontology-guided extraction | the model, priced |
| IF-26 | ABB-022 Model access and ledger | ABB-014 Answering agent | the model, priced |
| IF-27 | ABB-021 Evaluation runner and scorer | ABB-014 Answering agent | evaluation questions |

## Scenarios

The scenarios are the use cases': UC-001 S1 to S3 for answering, UC-002 for the sweep, UC-003 to UC-005 for the ontology lifecycle, UC-006 for tables, UC-007 for evaluation, UC-008 for scope. Each step of each is a call across one of the interfaces above.

<!-- deck:slide label="Controls" -->

## Controls

| Control | Where | What it stops |
|---|---|---|
| The scope rule at every hop | ABB-020 | A public caller reading private content |
| Claims checked by code | ABB-015 | An invented quote, value or figure |
| Fixed tools | ABB-012 | Writes, free queries, escape from scope |
| Valves | ABB-016 | Runaway cost per question, per person, per deployment |
| Publish refuses an understated bump | ABB-006 | A silent semantic change |
| Candidates stay out of the graph | ABB-007 | Document text changing the ontology |
| Documents as data | ABB-003, ABB-009 | Document text being executed or trusted |

<!-- deck:slide label="Decisions" -->

## Decisions

ADR-001 to ADR-005 and ADR-010 are this pattern's; ADR-006 to ADR-009 belong to REF-001.
