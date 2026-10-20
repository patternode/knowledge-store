---
kind: bounded-context
id: BC-004
title: "BC-004 Knowledge graph"
description: "The record per document, its projections and the fixed queries over them: keeping gold as the record, rebuilding the index, the SPARQL store, the optional backends and the passage index from it, and answering read-only questions filtered by scope."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
part_of: PL-001
contains: [ABB-011, ABB-013, ABB-012, ABB-025, ABB-026]
realises_capabilities: [CAP-005, CAP-006, CAP-007]
subdomain_kind: core
c4_levels: [container, component]
ubiquitous_language:
  - { term: "Record", definition: "Gold N-Quads per document per version, the union along the chain; everything else is rebuilt from it" }
  - { term: "Projection", definition: "A store rebuilt from the record for query: the index JSON, Neptune, Neo4j, AGE, MongoDB, the passage index" }
  - { term: "Pointer", definition: "gold/graph.json, documents.json, sparql.json, kb.json: which build a projection holds and whether it is served" }
  - { term: "Named graph", definition: "One per document per version, plus one for the ontology (the T-Box)" }
  - { term: "Adjacency", definition: "The two primitives any backend answers: a node by id, the relations of a set of nodes; traversal is the same code over them" }
  - { term: "Fixed tool", definition: "A query the store defines, never free SPARQL or Cypher, so a shared endpoint can enforce scope" }
  - { term: "Visible", definition: "Within the caller's scope: a public caller sees only what public documents say, by graph, entity, relation and passage" }
  - { term: "Figure", definition: "A metric or an ad hoc aggregate over a snapshot, with an id that names its computation" }
relationships:
  - { with: BC-003, pattern: customer-supplier, role: downstream }
  - { with: BC-002, pattern: published-language, role: downstream }
  - { with: BC-005, pattern: open-host-service, role: upstream }
  - { with: BC-006, pattern: open-host-service, role: upstream }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# BC-004 Knowledge graph

| Property | Value |
|---|---|
| Context ID | BC-004 |
| Platform | PL-001 Knowledge Store |
| Owner team | Patternode (Dermot O'Brien) |
| Subdomain | core |
| Realises | CAP-005, CAP-006, CAP-007 |
| Contains | ABB-011, ABB-013, ABB-012, ABB-025, ABB-026 |

The record per document, its projections and the fixed queries over them: keeping gold as the record, rebuilding the index, the SPARQL store, the optional backends and the passage index from it, and answering read-only questions filtered by scope.

## Ubiquitous language

| Term | Meaning in this context |
|---|---|
| Record | Gold N-Quads per document per version, the union along the chain; everything else is rebuilt from it |
| Projection | A store rebuilt from the record for query: the index JSON, Neptune, Neo4j, AGE, MongoDB, the passage index |
| Pointer | gold/graph.json, documents.json, sparql.json, kb.json: which build a projection holds and whether it is served |
| Named graph | One per document per version, plus one for the ontology (the T-Box) |
| Adjacency | The two primitives any backend answers: a node by id, the relations of a set of nodes; traversal is the same code over them |
| Fixed tool | A query the store defines, never free SPARQL or Cypher, so a shared endpoint can enforce scope |
| Visible | Within the caller's scope: a public caller sees only what public documents say, by graph, entity, relation and passage |
| Figure | A metric or an ad hoc aggregate over a snapshot, with an id that names its computation |

## Where the model lives today

- `knowledge_graph/ports.py` (GraphStore, Adjacency, ReadModel, SparqlStore, PassageSearch)
- `knowledge_graph/domain/` (traversal, the rows a property graph loads)
- `knowledge_graph/slices/` (project: gold to the index; tools: the read tools every surface calls; table_query: lookups over bound tables)
- `knowledge_graph/adapters/` (index and docstore: the read model in memory and in MongoDB; sparql: Neptune and in process; neo4j, age, backends; loading: the projection into each store; passages: Knowledge Base and keyword search; gateway: the Gateway's Lambda)

The index is loaded into one process from JSON and cached a minute; the SPARQL index answers the same questions over Neptune; backends bind only while the pointer names the served build. The read tools are one slice (`slices/tools.py`) that the Gateway's Lambda, the in-process agent and the portal's fallback chat all call, so they cannot drift apart.

## Relationships with other contexts

| With | Pattern | Role | Why |
|---|---|---|---|
| BC-003 | customer-supplier | downstream | Gold is the input |
| BC-002 | published-language | downstream | Renditions for the stores and the T-Box |
| BC-005 | open-host-service | upstream | The tools are the service the agent and the portal's loop consume |
| BC-006 | open-host-service | upstream | The portal API reads the index through Knowledge Graph's contract, as the tools do |

## Building blocks

ABB-011 Knowledge graph, ABB-013 Passage index, ABB-012 Graph tools, ABB-025 Passage tools and ABB-026 Tool gateway, each a page under [../abbs](../../abbs/README.md). The projection and loading code runs as components of ABB-024 in the pipeline container (CN-006).
