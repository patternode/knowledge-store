# Capability model

What the store must be able to do, independent of how. One L1 capability, grounded knowledge from documents, and twelve L2 capabilities, each provided by PL-001 and realised by the architecture building blocks named on its page. The register is [capabilities.csv](../capabilities.csv).

| Capability | Subdomain | Realised by |
|---|---|---|
| [CAP-001 Grounded knowledge from documents](CAP-001-grounded-knowledge-from-documents/index.md) | core | its L2 capabilities |
| [CAP-002 Document ingestion and passage derivation](CAP-002-document-ingestion-and-passage-derivation/index.md) | supporting | ABB-024, ABB-002 |
| [CAP-003 Ontology lifecycle management](CAP-003-ontology-lifecycle-management/index.md) | core | ABB-024, ABB-002, ABB-028 |
| [CAP-004 Fact extraction with provenance](CAP-004-fact-extraction-with-provenance/index.md) | core | ABB-024 |
| [CAP-005 Knowledge graph projection and query](CAP-005-knowledge-graph-projection-and-query/index.md) | core | ABB-011, ABB-012, ABB-024 |
| [CAP-006 Passage search by meaning](CAP-006-passage-search-by-meaning/index.md) | supporting | ABB-013, ABB-025, ABB-024 |
| [CAP-007 Structured lookup](CAP-007-structured-lookup/index.md) | core | ABB-024, ABB-012 |
| [CAP-008 Grounded answering](CAP-008-grounded-answering/index.md) | core | ABB-014 |
| [CAP-009 Access control by scope](CAP-009-access-control-by-scope/index.md) | supporting | ABB-020, ABB-027, ABB-026, ABB-012, ABB-025, ABB-019, ABB-018 |
| [CAP-010 Cost and spend control](CAP-010-cost-and-spend-control/index.md) | supporting | ABB-014, ABB-019 |
| [CAP-011 Answer evaluation](CAP-011-answer-evaluation/index.md) | supporting | ABB-021 |
| [CAP-012 Answer transparency and curation feedback](CAP-012-answer-transparency-and-curation-feedback/index.md) | core | ABB-014, ABB-018, ABB-019 |
| [CAP-013 Self-contained deployment and operation](CAP-013-self-contained-deployment-and-operation/index.md) | generic | ABB-028 |

Maturity is read from the implementation at release 0.3.0: a capability that is built, tested and in service is 4 (Managed); 3 (Defined) where the capability exists but a stated part is missing. The definition ladder's rungs are derived, not recorded: every L2 capability has ABBs (R2), the decisions in [../../decisions](../../decisions) resolve the considerations that affect them (R3), the SBBs name the technologies (R4), the evaluation sets and the lab are evidence (R5), and the deployment guide is the runbook (R6). Run the rung tool against the bindings to confirm rather than trust this paragraph.
