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
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# PAT-001 Ontology-driven GraphRAG with grounded answers

The logical pattern: technology-agnostic, in architecture building blocks. REF-001 is its physical form on AWS. Every use case in [../../problem/use-cases](../../../problem/use-cases/README.md) is realised by this pattern, and its scenarios walk theirs across the blocks named here; in UML terms this document is the use-case realization and the pattern it applies, in one.

## Context

An organisation has documents and wants to answer questions from them with every statement checkable. Retrieval over chunks answers fluently and unverifiably; a graph answers precisely but only in the terms someone defined. The pattern joins the two under an ontology a person owns: documents become passages, passages become typed facts that cite them, the facts are the record, projections serve queries, and an agent answers through fixed tools with claims that code checks before anything is shown.

The audience is a team building a knowledge store over its own documents, in any domain, who will own the ontology.

### Non-goals

- A general chat assistant: the agent answers from the collection or abstains.
- A model as judge of truth: every check is code, with the guardrail as a second, bounded opinion.
- Free querying by the model: the tools are fixed.
- A document management system: sources are read, never managed.

### Quality attributes

| Quality attribute | Scenario | Response measure |
|---|---|---|
| Groundedness | A model proposes a claim whose quote is not in the passage | The claim is repaired once or removed; it never reaches the page |
| Scope safety | A public caller's model asks a tool for private content | The interceptor sets the scope; the tool returns public content only |
| Cost | A question runs away in tool calls | The hook cancels the seventeenth call; the agent answers from what it has |
| Rebuildability | A projection is lost | The next sweep rebuilds it from gold; the pointer moves when counts check |
| Governance | A term is proposed from a document | It stays a candidate until a person publishes a version containing it |

## Diagram

The component view is the as-built diagram in REF-001 ([../../../aws/architecture.svg](../../../aws/architecture.svg)) read with the ABB labels below; a logical draw.io is to be emitted from the Required Building Blocks table with the model tool.

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

## Interfaces

| Interface | Provider | Consumer | Purpose |
|---|---|---|---|
| IF-01 | ABB-002 | every block | the lake port and layout |
| IF-02 | ABB-006 | ABB-009, ABB-011, ABB-014 | renditions per version |
| IF-03 | ABB-012 | ABB-014 | fixed tools as the caller |
| IF-04 | ABB-013 | ABB-014 | passage search and read |
| IF-05 | ABB-014 | ABB-019 | the answer, steps streamed |
| IF-06 | ABB-020 | ABB-012, ABB-014, ABB-019 | who is asking; the scope |
| IF-07 | ABB-022 | ABB-005, ABB-009, ABB-014 | the model, priced |
| IF-08 | ABB-017 | ABB-007 | ontology requests |

## Scenarios

The scenarios are the use cases': UC-001 S1 to S3 for answering, UC-002 for the sweep, UC-003 to UC-005 for the ontology lifecycle, UC-006 for tables, UC-007 for evaluation, UC-008 for scope. Each step of each is a call across one of the interfaces above.

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

## Decisions

ADR-001 to ADR-005 and ADR-010 are this pattern's; ADR-006 to ADR-009 belong to REF-001.
