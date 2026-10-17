# Architecture building blocks

Logical, technology-agnostic, each inside one bounded context, each with published interfaces and the three cross-cutting sections the standard requires. Twenty-three, reversed from the implementation at 0.3.0. The register is [../abbs.csv](../abbs.csv); each page names the code that holds it today.

| ABB | Context | Realises | Realised by |
|---|---|---|---|
| [ABB-001 Source adapters](ABB-001-source-adapters/index.md) | BC-001 | CAP-002 | SBB-014 |
| [ABB-002 Lake and layering](ABB-002-lake-and-layering/index.md) | BC-001 | CAP-002 | SBB-001, SBB-013 |
| [ABB-003 Document refinement](ABB-003-document-refinement/index.md) | BC-001 | CAP-002 | SBB-014 |
| [ABB-004 Sweep orchestration](ABB-004-sweep-orchestration/index.md) | BC-001 | CAP-002 | SBB-002, SBB-013 |
| [ABB-005 Ontology discovery and review](ABB-005-ontology-discovery-and-review/index.md) | BC-002 | CAP-003 | SBB-014, SBB-012 |
| [ABB-006 Ontology versioning and renditions](ABB-006-ontology-versioning-and-renditions/index.md) | BC-002 | CAP-003, CAP-007 | SBB-014 |
| [ABB-007 Candidate register and revision proposal](ABB-007-candidate-register-and-revision-proposal/index.md) | BC-002 | CAP-003, CAP-012 | SBB-014, SBB-012 |
| [ABB-008 Table mapping definition](ABB-008-table-mapping-definition/index.md) | BC-002 | CAP-007 | SBB-014 |
| [ABB-009 Ontology-guided extraction](ABB-009-ontology-guided-extraction/index.md) | BC-003 | CAP-004 | SBB-014, SBB-012 |
| [ABB-010 Table binding](ABB-010-table-binding/index.md) | BC-003 | CAP-004, CAP-007 | SBB-014 |
| [ABB-011 Graph record and projection](ABB-011-graph-record-and-projection/index.md) | BC-004 | CAP-005 | SBB-003, SBB-011, SBB-014 |
| [ABB-012 Fixed query tools](ABB-012-fixed-query-tools/index.md) | BC-004 | CAP-005, CAP-007, CAP-009 | SBB-005, SBB-007, SBB-013 |
| [ABB-013 Passage search by meaning](ABB-013-passage-search-by-meaning/index.md) | BC-004 | CAP-006 | SBB-004, SBB-005 |
| [ABB-014 Answering agent](ABB-014-answering-agent/index.md) | BC-005 | CAP-008 | SBB-006, SBB-007, SBB-013 |
| [ABB-015 Claim grounding and checks](ABB-015-claim-grounding-and-checks/index.md) | BC-005 | CAP-008 | SBB-006 |
| [ABB-016 Valves and quotas](ABB-016-valves-and-quotas/index.md) | BC-005 | CAP-010 | SBB-006, SBB-007 |
| [ABB-017 Workbench](ABB-017-workbench/index.md) | BC-005 | CAP-012 | SBB-006, SBB-007 |
| [ABB-018 Chat page](ABB-018-chat-page/index.md) | BC-006 | CAP-009, CAP-012 | SBB-007 |
| [ABB-019 Chat API](ABB-019-chat-api/index.md) | BC-006 | CAP-009, CAP-010 | SBB-007, SBB-013 |
| [ABB-020 Identity and scope](ABB-020-identity-and-scope/index.md) | BC-006 | CAP-009 | SBB-008, SBB-005, SBB-007 |
| [ABB-021 Evaluation runner and scorer](ABB-021-evaluation-runner-and-scorer/index.md) | BC-007 | CAP-011 | SBB-013, SBB-007 |
| [ABB-022 Model access and ledger](ABB-022-model-access-and-ledger/index.md) | BC-008 | CAP-010 | SBB-012 |
| [ABB-023 Deployment automation](ABB-023-deployment-automation/index.md) | BC-008 | CAP-013 | SBB-009, SBB-010, SBB-013 |

The requires relations form a directed graph with no cycles: ingestion and the lake at the bottom, the ontology and extraction above them, the graph and its tools above those, answering and the portal at the top, with identity and the platform services beside. The two cycles the code has (between the tools and the portal's index, and between the SPARQL index and the portal) are not in the logical model; they are the as-built seams CN-006 names.
