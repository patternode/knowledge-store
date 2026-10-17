# Architecture building blocks

Logical, technology-agnostic, each inside one bounded context, each with published interfaces and the three cross-cutting sections the standard requires. Twelve, reversed from the implementation at 0.3.0 and recalibrated to container grain on 2026-10-17: each is one C4 container, a separately deployed unit or a store with its own lifecycle, per the [building block calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md). What runs inside a container is listed on its page as components, never as a block of its own. The register is [../abbs.csv](../abbs.csv).

| ABB | Context | Realises | Realised by |
|---|---|---|---|
| [ABB-002 Lake and layering](ABB-002-lake-and-layering/index.md) | BC-001 | CAP-002 | SBB-001 |
| [ABB-004 Pipeline sweep](ABB-004-pipeline-sweep/index.md) | BC-003 | CAP-002 | SBB-002 |
| [ABB-006 Ontology publisher](ABB-006-ontology-publisher/index.md) | BC-002 | CAP-003, CAP-007 | SBB-015 |
| [ABB-011 Knowledge graph store](ABB-011-knowledge-graph-store/index.md) | BC-004 | CAP-005 | SBB-003, SBB-011 |
| [ABB-012 Tool gateway and fixed query tools](ABB-012-tool-gateway-and-fixed-query-tools/index.md) | BC-004 | CAP-005, CAP-007, CAP-009 | SBB-005 |
| [ABB-013 Passage index](ABB-013-passage-index/index.md) | BC-004 | CAP-006 | SBB-004 |
| [ABB-014 Answering agent](ABB-014-answering-agent/index.md) | BC-005 | CAP-008 | SBB-006 |
| [ABB-018 Chat page](ABB-018-chat-page/index.md) | BC-006 | CAP-009, CAP-012 | SBB-016 |
| [ABB-019 Chat API](ABB-019-chat-api/index.md) | BC-006 | CAP-009, CAP-010 | SBB-007 |
| [ABB-020 Identity](ABB-020-identity/index.md) | BC-006 | CAP-009 | SBB-008 |
| [ABB-021 Evaluation runner and scorer](ABB-021-evaluation-runner-and-scorer/index.md) | BC-007 | CAP-011 | SBB-015 |
| [ABB-023 Image build](ABB-023-image-build/index.md) | BC-008 | CAP-013 | SBB-009 |

The requires relations form a directed graph with no cycles: the lake at the bottom, the sweep and the publisher above it, the graph and passage stores above those, the gateway and tools above them, the agent, the API and the page at the top, with identity and the image build beside. The seams the code still has inside the sweep and the chat API are the as-built findings CN-006 names; the folds below made them components rather than blocks.

## Retired identifiers

Eleven identifiers were retired in the recalibration. Each was a component of a container, not a container, and its content now sits in section 2.2 of the block it folded into. An identifier is never reused.

| Retired | Was | Folded into | Why |
|---|---|---|---|
| ABB-001 | Source adapters | ABB-004 | adapters run inside the sweep's process |
| ABB-003 | Document refinement | ABB-004 | a stage of the sweep |
| ABB-005 | Ontology discovery and review | ABB-004 | a stage of the sweep |
| ABB-007 | Candidate register and revision proposal | ABB-004 | written by extraction inside the sweep; proposed by the publisher |
| ABB-008 | Table mapping definition | ABB-006 | part of what a curator publishes with a version |
| ABB-009 | Ontology-guided extraction | ABB-004 | a stage of the sweep |
| ABB-010 | Table binding | ABB-004 | a stage of the sweep |
| ABB-015 | Claim grounding and checks | ABB-014 | runs in the agent's process |
| ABB-016 | Valves and quotas | ABB-014 | hooks in the agent's process; the daily count at the chat API (ABB-019) |
| ABB-017 | Workbench | ABB-014 | the recorder in the agent's process; the panel in the chat page (ABB-018) |
| ABB-022 | Model access and ledger | ABB-004 | a library each caller carries; the ledger is a prefix of the lake (ABB-002); the agent's copy is in ABB-014 |
