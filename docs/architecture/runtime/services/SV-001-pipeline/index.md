---
kind: service
id: pipeline
numeric_id: SV-001
title: "SV-001 Pipeline (the sweep)"
description: "The Fargate task that runs one sweep over every collection: ingest, refine, discover or publish, extract, bind, candidates, project, load the graph, the backends, Neptune and the passage index, and write the status."
version: 0.1.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [SBB-002]
part_of: BC-001
composes_contexts: [BC-001, BC-002, BC-003, BC-004]
runtime_type: container
repo: { url: "https://github.com/patternode/knowledge-store", path: "." }
module_path: "src/knowledge_store/apps/sweep.py"
packages: ["knowledge_store.apps.sweep", "knowledge_store.ingestion", "knowledge_store.ontology", "knowledge_store.extraction", "knowledge_store.knowledge_graph", "knowledge_store.platform_services"]
deployed_to: [DN-004]
run_by: "PRD-001; started by uploads and a schedule"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SV-001 Pipeline (the sweep)

The Fargate task that runs one sweep over every collection: ingest, refine, discover or publish, extract, bind, candidates, project, load the graph, the backends, Neptune and the passage index, and write the status.

| Field | Value |
|---|---|
| Identifier | SV-001, slug `pipeline` |
| Kind | Service, container |
| Context | BC-001; composes BC-001, BC-002, BC-003, BC-004 as built |
| Realises | SBB-002 |
| Node | DN-004 |
| Code | `src/knowledge_store/apps/sweep.py (entry: knowledge-store run)` |
| Talks to | The lake; the extraction model through Bedrock or the Anthropic API; Neptune (write); the Knowledge Base ingestion job; the optional backends. |
| Stores | Writes bronze, silver, gold, ontology versions and drafts, the candidate register, the index, the pointers, kb/passages, the lock, the status and the ledger; reads collection configuration. |
| Role | <name>-pipeline-task: the lake, configured source buckets, the extraction model, the Anthropic key secret, Neptune connect, read, write and delete, Knowledge Base ingestion jobs. |
| Run by | PRD-001; started by uploads and a schedule |

## Up the thread

From this running unit to the reason it exists: the SBB it realises names the technologies, the ABBs those realise are inside the contexts it composes, the contexts realise the capabilities, and the capabilities serve the outcomes of PL-001. Every link exists in this catalogue; the registers answer the queries in both directions.

## Findings against the continuum

| Finding | Rule | Where it is addressed |
|---|---|---|
| One process composes four contexts | A service serves one bounded context | CN-006: the stages are already separable by the lake layout; each could be a task of its own |
| The sweep writes every store | A store is owned by one context | As designed: the sweep is the only writer, which is the security rule; ownership by context is recorded in stores.csv |

