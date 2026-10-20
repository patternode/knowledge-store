---
kind: service
id: agent-interceptor
numeric_id: SV-006
title: "SV-006 Gateway interceptor"
description: "The REQUEST interceptor that decodes the verified bearer token and overwrites caller_private on every tools/call, so the model cannot ask for more than the person may read."
version: 0.1.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [SBB-017]
part_of: BC-006
composes_contexts: [BC-006]
runtime_type: serverless
repo: { url: "https://github.com/patternode/knowledge-store", path: "." }
module_path: "src/knowledge_store/access/adapters/gateway_interceptor.py"
packages: ["knowledge_store.access.adapters.gateway_interceptor", "knowledge_store.access.domain.claims"]
deployed_to: [DN-007]
run_by: "PRD-001; run by the Gateway on every call"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SV-006 Gateway interceptor

The REQUEST interceptor that decodes the verified bearer token and overwrites caller_private on every tools/call, so the model cannot ask for more than the person may read.

| Field | Value |
|---|---|
| Identifier | SV-006, slug `agent-interceptor` |
| Kind | Service, serverless |
| Context | BC-006; composes BC-006 as built |
| Realises | SBB-017 |
| Node | DN-007 |
| Code | `src/knowledge_store/access/adapters/gateway_interceptor.py (lambda_handler)` |
| Talks to | Nothing. |
| Stores | None. |
| Role | <name>-agent-interceptor: logs only. |
| Run by | PRD-001; run by the Gateway on every call |

## Up the thread

From this running unit to the reason it exists: the SBB it realises names the technologies, the ABBs those realise are inside the contexts it composes, the contexts realise the capabilities, and the capabilities serve the outcomes of PL-001. Every link exists in this catalogue; the registers answer the queries in both directions.

## Findings against the continuum

| Finding | Rule | Where it is addressed |
|---|---|---|
| Its log group is not managed by Terraform | Every unit provisioned from code | No retention set; a small follow-up |

