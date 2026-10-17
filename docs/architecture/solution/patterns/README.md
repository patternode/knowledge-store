# Patterns

One construct at two abstractions: PAT-001 is the logical pattern in ABBs, REF-001 is its physical form in SBBs on AWS. Both are C4 container views: every box is one container, per the building block calibration standard, and what runs inside a container is on its block's page. Every use case names both in `realised_by`, and REF-001 carries the cost model, the evidence and the runbook references the definition ladder reads.

| Pattern | Abstraction | Realises | Implements |
|---|---|---|---|
| [PAT-001 Ontology-driven GraphRAG with grounded answers](PAT-001-ontology-driven-graphrag/index.md) | logical | CAP-003 to CAP-009 | |
| [REF-001 Knowledge Store on AWS](REF-001-knowledge-store-on-aws/index.md) | physical | CAP-002 to CAP-013 | PAT-001 |

Patternode's house repository keeps `pna:PAT-001` Knowledge Lab, `pna:PAT-004` Ontology-driven GraphRAG on Neo4j and `pna:PAT-005` Knowledge Lab MCP Server, written before this catalogue; they describe the same component from the lab's side and should cite `ks:PAT-001` and `ks:REF-001` rather than restate them.
