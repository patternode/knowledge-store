---
kind: service
id: tools-passages
numeric_id: SV-005
title: "SV-005 Passage tools"
description: "The two passage tools as a Gateway target outside the VPC: search by meaning through the Knowledge Base with the scope filter, or keyword fallback, and read by id from the projection or silver."
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
module_path: "src/knowledge_store/tools/gateway.py"
packages: ["knowledge_store.tools.passages", "knowledge_store.pipeline.refine (load_doc, load_passages)"]
deployed_to: [DN-007]
run_by: "PRD-001; called by the Gateway"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SV-005 Passage tools

The two passage tools as a Gateway target outside the VPC: search by meaning through the Knowledge Base with the scope filter, or keyword fallback, and read by id from the projection or silver.

| Field | Value |
|---|---|
| Identifier | SV-005, slug `tools-passages` |
| Kind | Service, serverless |
| Context | BC-004; composes BC-004 as built |
| Realises | SBB-005 |
| Node | DN-007 |
| Code | `src/knowledge_store/tools/gateway.py (lambda_handler, TOOLSET=passages)` |
| Talks to | Bedrock Retrieve; the lake's gold, silver, ontology and config prefixes. |
| Stores | Reads only. |
| Role | <name>-tools-passages: read those layers; bedrock:Retrieve on the Knowledge Base. |
| Run by | PRD-001; called by the Gateway |

## Up the thread

From this running unit to the reason it exists: the SBB it realises names the technologies, the ABBs those realise are inside the contexts it composes, the contexts realise the capabilities, and the capabilities serve the outcomes of PL-001. Every link exists in this catalogue; the registers answer the queries in both directions.

## Findings against the continuum

None.
