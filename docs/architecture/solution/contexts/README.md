# Bounded contexts

Where one model and one language hold. Eight contexts inside PL-001, each with its ubiquitous language, the modules that hold its model today, and its relationships with the others in strategic DDD terms. The register is [../contexts.csv](../contexts.csv).

The contexts are the ones the code suggests, not yet the ones it is deployed as: the pipeline image composes BC-001 to BC-004 in one process and the agent image composes BC-004's tools with BC-005. The services register ([../../runtime/services.csv](../../runtime/services.csv)) says what each deployable composes, and CN-006 holds the decoupling question. The two dependency cycles the surveys found (the tools Lambda importing the portal's index and chat modules; the SPARQL index importing the portal's index at call time) are where the boundary between BC-004 and BC-006 is not yet cut.

| Context | Subdomain | Realises | Contains |
|---|---|---|---|
| [BC-001 Ingestion](BC-001-ingestion/index.md) | supporting | CAP-002 | ABB-002, ABB-024 |
| [BC-002 Ontology](BC-002-ontology/index.md) | core | CAP-003, CAP-007 | ABB-024 |
| [BC-003 Extraction](BC-003-extraction/index.md) | core | CAP-004, CAP-007 | ABB-024 |
| [BC-004 Knowledge graph](BC-004-knowledge-graph/index.md) | core | CAP-005, CAP-006, CAP-007 | ABB-011, ABB-013, ABB-012, ABB-025, ABB-026 |
| [BC-005 Answering](BC-005-answering/index.md) | core | CAP-008, CAP-010, CAP-012 | ABB-014 |
| [BC-006 Portal and identity](BC-006-portal-and-identity/index.md) | supporting | CAP-009, CAP-010 | ABB-018, ABB-019, ABB-020, ABB-027 |
| [BC-007 Evaluation](BC-007-evaluation/index.md) | supporting | CAP-011 | ABB-021 |
| [BC-008 Platform services](BC-008-platform-services/index.md) | generic | CAP-010, CAP-013 | ABB-028 |

## Context map

![The context map: Ingestion supplies Extraction, which supplies Knowledge graph, an open host to Answering; Ontology publishes its language to both and receives candidates from Answering; Portal and identity invokes Answering as the person and shares the index module with Knowledge graph; Evaluation asks Answering; Platform services is an open host every context uses](./context-map.svg)
