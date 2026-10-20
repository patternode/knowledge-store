---
kind: service
id: tools-graph
numeric_id: SV-004
title: "SV-004 Graph tools"
description: "The ten graph and table tools as a Gateway target in the private subnets, reading Neptune read-only or the index, with caller_private from the interceptor."
version: 0.1.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [SBB-005]
part_of: BC-004
composes_contexts: [BC-004]
runtime_type: serverless
repo: { url: "https://github.com/patternode/knowledge-store", path: "." }
module_path: "src/knowledge_store/knowledge_graph/adapters/gateway.py"
packages: ["knowledge_store.knowledge_graph"]
deployed_to: [DN-007, DN-006]
run_by: "PRD-001; called by the Gateway"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SV-004 Graph tools

The ten graph and table tools as a Gateway target in the private subnets, reading Neptune read-only or the index, with caller_private from the interceptor.

| Field | Value |
|---|---|
| Identifier | SV-004, slug `tools-graph` |
| Kind | Service, serverless |
| Context | BC-004; composes BC-004 as built |
| Realises | SBB-005 |
| Node | DN-007, DN-006 |
| Code | `src/knowledge_store/knowledge_graph/adapters/gateway.py (lambda_handler, TOOLSET=graph)` |
| Talks to | Neptune over SPARQL with SigV4; the lake's gold, ontology and config prefixes. |
| Stores | Reads only. |
| Role | <name>-tools-graph: read config and the collections' gold, ontology and config layers; Neptune connect and read; VPC networking. |
| Run by | PRD-001; called by the Gateway |

## Up the thread

From this running unit to the reason it exists: the SBB it realises names the technologies, the ABBs those realise are inside the contexts it composes, the contexts realise the capabilities, and the capabilities serve the outcomes of PL-001. Every link exists in this catalogue; the registers answer the queries in both directions.

## Findings against the continuum

| Finding | Rule | Where it is addressed |
|---|---|---|
| Imports the portal package's index and chat modules | Context integrity | The index belongs to BC-004; it lives under portal_api today (CN-006) |

