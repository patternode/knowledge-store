---
kind: capability
id: CAP-005
title: "CAP-005 Knowledge graph projection and query"
description: "Keeping the extracted RDF as the record, projecting it into the stores that answer queries (an index, a SPARQL store, optional graph and document backends), and answering fixed read-only questions in the ontology's terms, filtered to what the caller may read."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
level: L2
parent: CAP-001
components:
  organisation: "The sweep loads; the tools read; the administrator chooses the backends"
  people: ["Administrators (backends, Neptune size)", "Readers and agents (the tools)"]
  processes:
    - "Project gold to the index JSON after every sweep"
    - "Load named graphs into Neptune, skipping unchanged ones"
    - "Load optional Neo4j, AGE or MongoDB projections and move the pointer only when counts check"
    - "Serve search, entity, neighbourhood, path and structured lookups through fixed queries"
    - "Filter every answer by the caller's scope"
  technology: "N-Quads with named graphs, an in-memory index, SPARQL over Neptune with SigV4, the GraphStore and Adjacency protocols, MongoDB documents, fixed tool definitions"
maturity:
  current: 4
  target: 4
  assessment_date: 2026-10-16
  assessor: "Patternode (Dermot O'Brien), reversed from the implementation"
subdomain_kind: core
provided_by_platform: PL-001
realised_by_abbs: [ABB-011, ABB-012, ABB-024]
gaps:
  - "The in-memory index is right for tens of thousands of entities; beyond that MongoDB is the projection (CN-001, CN-005)"
  - "Passage search over SPARQL is not implemented; the Knowledge Base or the keyword index serves it"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# CAP-005 Knowledge graph projection and query

| Property | Value |
|---|---|
| Capability ID | CAP-005 |
| Level | L2 |
| Parent | CAP-001 |
| Status | Draft, reversed from the implementation at 0.3.0 |
| Subdomain | core |
| Maturity | 4, target 4 |
| Realised by | ABB-011, ABB-012, ABB-024 |

Keeping the extracted RDF as the record, projecting it into the stores that answer queries (an index, a SPARQL store, optional graph and document backends), and answering fixed read-only questions in the ontology's terms, filtered to what the caller may read.

## 1  Purpose

The record and the things that are fast to query are not the same store. This capability keeps gold as the record, rebuilds projections from it with pointers that say which build is served, and exposes only fixed tools, so a shared endpoint can enforce scope and nothing can write.

## 2  Capability definition

| Dimension | For Knowledge Store |
|---|---|
| Organisation | The sweep loads; the tools read; the administrator chooses the backends |
| People | Administrators (backends, Neptune size), Readers and agents (the tools) |
| Processes | Project gold to the index JSON after every sweep; Load named graphs into Neptune, skipping unchanged ones; Load optional Neo4j, AGE or MongoDB projections and move the pointer only when counts check; Serve search, entity, neighbourhood, path and structured lookups through fixed queries; Filter every answer by the caller's scope |
| Technology | N-Quads with named graphs, an in-memory index, SPARQL over Neptune with SigV4, the GraphStore and Adjacency protocols, MongoDB documents, fixed tool definitions |

## 3  Sub-capabilities

| Sub-capability | What it covers | Status |
|---|---|---|
| The record | Gold N-Quads per document per version, chained | In place |
| Projection | Index, SPARQL store, optional backends, with pointers | In place |
| Fixed query tools | Entities, neighbourhoods, paths, tables, aggregates | In place |
| Scope filtering | Public callers see only what public documents say | In place |

## 4  What the implementation does today

Gold per version is the union along the chain. The index JSON is loaded into one process and cached for 60 seconds. Neptune holds one named graph per document plus the T-Box; the graph tools Lambda reads it with a read-only role. Backends are filled by the load stage and bound only while the lake's pointer names the served build. Twelve fixed tools, ten over the graph and tables and two over passages, with no free SPARQL or Cypher.

## 5  Maturity

Current maturity is 4 on the 0 to 5 scale, read from the implementation: the capability is defined, built and in service in the Patternode lab and in any deployment of the module. Target 4.

## 6  Gaps

- The in-memory index is right for tens of thousands of entities; beyond that MongoDB is the projection (CN-001, CN-005)
- Passage search over SPARQL is not implemented; the Knowledge Base or the keyword index serves it
