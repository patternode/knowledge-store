# Architecture patterns and reference architectures

The two kinds of pattern document the continuum names, and never a pattern on its own: AP-001 is the architecture pattern, technology-agnostic in ABBs at logical abstraction; RA-001 is the reference architecture, technology-specific in SBBs on AWS, and it applies AP-001. Every use case names both in `realised_by`, and RA-001 carries the cost model, the evidence and the runbook references the definition ladder reads.

| Document | Type and abstraction | Realises | Implements |
|---|---|---|---|
| [AP-001 Ontology-driven GraphRAG with grounded answers](AP-001-ontology-driven-graphrag/index.md) | architecture pattern, logical | CAP-003 to CAP-009 | |
| [RA-001 Knowledge Store on AWS](RA-001-knowledge-store-on-aws/index.md) | reference architecture, physical | CAP-002 to CAP-013 | AP-001 |

Patternode's house repository keeps `pna:PAT-001` Knowledge Lab, `pna:PAT-004` Ontology-driven GraphRAG on Neo4j and `pna:PAT-005` Knowledge Lab MCP Server, written before this catalogue; they describe the same component from the lab's side and should cite `ks:AP-001` and `ks:RA-001` rather than restate them.
