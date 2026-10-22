# Decisions and considerations

A consideration is an open question with more than one credible answer; a decision record settles one. Both are reversed from the implementation and the design notes at 0.3.0: the decisions were made in code and in `docs/architecture/*.md` before they were written in this form. Registers: [decisions.csv](decisions.csv), [considerations.csv](considerations.csv).

## Decisions

| Decision | Affects |
|---|---|
| [ADR-001 Gold RDF per document is the record; everything else is a projection](ADR-001-gold-rdf-per-document-is-the-record-everything-else-is-a-projection.md) | BC-003, BC-004, ABB-011, ABB-002 |
| [ADR-002 Nothing is shown unchecked: claims with citations, verified by code](ADR-002-nothing-is-shown-unchecked-claims-with-citations-verified-by-code.md) | BC-005, ABB-014 |
| [ADR-003 The person's identity goes all the way down](ADR-003-the-person-s-identity-goes-all-the-way-down.md) | BC-006, ABB-020, ABB-012 |
| [ADR-004 Fixed tools, never free SPARQL or Cypher](ADR-004-fixed-tools-never-free-sparql-or-cypher.md) | BC-004, ABB-012 |
| [ADR-005 Ontology versions are immutable and classified, and the bump decides the cost](ADR-005-ontology-versions-are-immutable-and-classified-and-the-bump-decides-the-cost.md) | BC-002, ABB-024 |
| [ADR-006 One Terraform module, images built inside the account](ADR-006-one-terraform-module-images-built-inside-the-account.md) | BC-008,  |
| [ADR-007 A passage index on S3 Vectors beside the graph](ADR-007-a-passage-index-on-s3-vectors-beside-the-graph.md) | BC-004, ABB-013 |
| [ADR-008 Memory is the default projection; graph and document backends are optional](ADR-008-memory-is-the-default-projection-graph-and-document-backends-are-optional.md) | BC-004, ABB-011 |
| [ADR-009 A mapped table stays a file, bound at a snapshot into gold](ADR-009-a-mapped-table-stays-a-file-bound-at-a-snapshot-into-gold.md) | BC-003, ABB-024, ABB-012 |
| [ADR-010 Scope is the one access control today, stated per source](ADR-010-scope-is-the-one-access-control-today-stated-per-source.md) | BC-006, ABB-020 |
| [ADR-011 The code is cut by bounded context, and a deployable splits off only on a trigger](ADR-011-the-code-is-cut-by-bounded-context-and-deployables-split-on-a-trigger.md) | BC-001 to BC-008, SV-001 to SV-006, SV-009 |
| [ADR-012 Evaluation counts false answers and unsupported claims, and gates releases on a baseline](ADR-012-evaluation-counts-false-answers-and-unsupported-claims-and-gates-releases.md) | BC-007, BC-005, SV-009, ABB-021 |
| [ADR-013 DeepEval is the evaluation framework, beside the deterministic score](ADR-013-deepeval-is-the-evaluation-framework-beside-the-deterministic-score.md) | BC-007, SV-009, ABB-021, SBB-019 |

## Considerations

| Consideration | Status | Affects |
|---|---|---|
| [CN-001 Neptune or Neo4j as the graph for an organisation's collections](CN-001-neptune-or-neo4j-as-the-graph-for-an-organisation-s-collections/index.md) | open | CAP-005, ABB-011, SBB-003, SBB-011 |
| [CN-002 Controls a document carries of its own](CN-002-controls-a-document-carries-of-its-own/index.md) | resolved by ADR-010 | CAP-009, ABB-027, ABB-024 |
| [CN-003 Live structured sources through a virtual knowledge graph](CN-003-live-structured-sources-through-a-virtual-knowledge-graph/index.md) | resolved by ADR-009 | CAP-007, ABB-024, ABB-012 |
| [CN-004 Whether a vector store is needed beside the graph](CN-004-whether-a-vector-store-is-needed-beside-the-graph/index.md) | resolved, ADR-007 | CAP-006, ABB-013 |
| [CN-005 Where the projection and the chat state live at scale](CN-005-where-the-projection-and-the-chat-state-live-at-scale/index.md) | resolved, ADR-008 | CAP-005, ABB-011, ABB-019 |
| [CN-006 Decoupling the deployables along the bounded contexts](CN-006-decoupling-the-deployables-along-the-bounded-contexts/index.md) | resolved by ADR-011 | BC-001, BC-004, BC-005, BC-006, SV-001, SV-003, SV-004 |

The design notes that carry the reasoning in full stay where they are: [security.md](../../design/security.md) (ADR-002, ADR-003), [source-controls.md](../../design/source-controls.md) (CN-002, ADR-010), [aws/backends.md](../../design/aws/backends.md) (ADR-008), [aws/scalability.md](../../design/aws/scalability.md) (CN-001), [aws/structured.md](../../design/aws/structured.md) (ADR-009, CN-003) and [aws/aws.md](../../design/aws/aws.md) (ADR-007, the cost table).
