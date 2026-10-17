# Architecture building blocks

Logical, technology-agnostic, each inside one bounded context, each with published interfaces and the three cross-cutting sections the standard requires. Fourteen at container grain, recalibrated on 2026-10-17 under the [building block calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md): every block is one C4 container, a separately deployable unit that executes code or stores data, and nothing smaller. The register is [../abbs.csv](../abbs.csv), which also lists the retired identifiers; each page names the code that holds it today and the components it absorbed.

| ABB | Context | Realises | Realised by |
|---|---|---|---|
| [ABB-002 Lake](ABB-002-lake/index.md) | BC-001 | CAP-002, CAP-003 | SBB-001 |
| [ABB-024 Ingestion and extraction pipeline](ABB-024-ingestion-and-extraction-pipeline/index.md) | BC-001 | CAP-002, CAP-003, CAP-004, CAP-005, CAP-006, CAP-007 | SBB-002 |
| [ABB-011 Knowledge graph](ABB-011-knowledge-graph/index.md) | BC-004 | CAP-005 | SBB-003, SBB-011 |
| [ABB-013 Passage index](ABB-013-passage-index/index.md) | BC-004 | CAP-006 | SBB-004 |
| [ABB-012 Graph tools](ABB-012-graph-tools/index.md) | BC-004 | CAP-005, CAP-007, CAP-009 | SBB-005 |
| [ABB-025 Passage tools](ABB-025-passage-tools/index.md) | BC-004 | CAP-006, CAP-009 | SBB-015 |
| [ABB-026 Tool gateway](ABB-026-tool-gateway/index.md) | BC-004 | CAP-009 | SBB-016 |
| [ABB-027 Call interceptor](ABB-027-call-interceptor/index.md) | BC-006 | CAP-009 | SBB-017 |
| [ABB-014 Answering agent](ABB-014-answering-agent/index.md) | BC-005 | CAP-008, CAP-010, CAP-012 | SBB-006 |
| [ABB-019 Chat API](ABB-019-chat-api/index.md) | BC-006 | CAP-009, CAP-010, CAP-012 | SBB-007 |
| [ABB-018 Chat page](ABB-018-chat-page/index.md) | BC-006 | CAP-009, CAP-012 | SBB-018 |
| [ABB-020 Identity](ABB-020-identity/index.md) | BC-006 | CAP-009 | SBB-008 |
| [ABB-028 Command line](ABB-028-command-line/index.md) | BC-008 | CAP-002, CAP-003, CAP-004, CAP-005, CAP-007, CAP-008, CAP-010, CAP-013 | SBB-013 |
| [ABB-021 Evaluation runner](ABB-021-evaluation-runner/index.md) | BC-007 | CAP-011 | SBB-019 |

The first pass had twenty-three blocks, nine of which were components of the pipeline container and four of the agent. The calibration folded them: ABB-001 Source adapters into ABB-024, ABB-003 Document refinement into ABB-024, ABB-004 Sweep orchestration into ABB-024, ABB-005 Ontology discovery and review into ABB-024, ABB-006 Ontology versioning and renditions into ABB-024, ABB-007 Candidate register and revision proposal into ABB-024, ABB-008 Table mapping definition into ABB-024, ABB-009 Ontology-guided extraction into ABB-024, ABB-010 Table binding into ABB-024, ABB-015 Claim grounding and checks into ABB-014, ABB-016 Valves and quotas into ABB-014, ABB-017 Workbench into ABB-014, ABB-022 Model access and ledger into ABB-014, ABB-023 Deployment automation with no container. Their pages are gone; the register keeps each identifier as retired, with the container it folded into, so it is never reused.

ABB-024 composes four bounded contexts in one container today (CN-006): the ontology and extraction contexts, BC-002 and BC-003, have no container of their own, and their components run inside it. The requires relations still form a directed graph with no cycles: the lake at the bottom, the pipeline and the stores above it, the tools behind the gateway above those, the agent, the API and the page at the top, with identity, the interceptor and the operator commands beside.
