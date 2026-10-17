# Architecture patterns and reference architectures

The two kinds of pattern document the continuum names, and never a pattern on its own: PAT-001 is the architecture pattern, technology-agnostic in ABBs at logical abstraction; REF-001 is the reference architecture, technology-specific in SBBs on AWS, and it applies PAT-001. Every use case names both in `realised_by`, and REF-001 carries the cost model, the evidence and the runbook references the definition ladder reads.

| Document | Type and abstraction | Realises | Implements |
|---|---|---|---|
| [PAT-001 Ontology-driven GraphRAG with grounded answers](PAT-001-ontology-driven-graphrag/index.md) | architecture pattern, logical | CAP-003 to CAP-009 | |
| [REF-001 Knowledge Store on AWS](REF-001-knowledge-store-on-aws/index.md) | reference architecture, physical | CAP-002 to CAP-013 | PAT-001 |

Patternode's house repository keeps `pna:PAT-001` Knowledge Lab, `pna:PAT-004` Ontology-driven GraphRAG on Neo4j and `pna:PAT-005` Knowledge Lab MCP Server, written before this catalogue; they describe the same component from the lab's side and should cite `ks:PAT-001` and `ks:REF-001` rather than restate them.
