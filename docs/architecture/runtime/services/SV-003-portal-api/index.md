---
kind: service
id: portal-api
numeric_id: SV-003
title: "SV-003 Portal API"
description: "The Lambda behind API Gateway and CloudFront: every route of CT-001, the quota, asynchronous answering by self-invocation, the index-backed views, signed document and table links, and the fallback tool loop until the Runtime exists."
version: 0.1.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [SBB-007]
part_of: BC-006
composes_contexts: [BC-006, BC-004, BC-005]
runtime_type: serverless
repo: { url: "https://github.com/patternode/knowledge-store", path: "." }
module_path: "src/knowledge_store/portal_api/handler.py"
packages: ["knowledge_store.portal_api", "knowledge_store.site_grant", "knowledge_store.claims", "knowledge_store.workbench"]
deployed_to: [DN-007, DN-008]
run_by: "PRD-001"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SV-003 Portal API

The Lambda behind API Gateway and CloudFront: every route of CT-001, the quota, asynchronous answering by self-invocation, the index-backed views, signed document and table links, and the fallback tool loop until the Runtime exists.

| Field | Value |
|---|---|
| Identifier | SV-003, slug `portal-api` |
| Kind | Service, serverless |
| Context | BC-006; composes BC-006, BC-004, BC-005 as built |
| Realises | SBB-007 |
| Node | DN-007, DN-008 |
| Code | `src/knowledge_store/portal_api/handler.py (handler)` |
| Talks to | The lake (served prefixes; writes ontology requests); the chat table; the agent Runtime as the person or a service client; the chat model for the fallback loop; two secrets. |
| Stores | Writes chat#, quota# and usage# keys of the chat table and ontology/requests in the lake. |
| Role | <name>-portal-api: read served layers, write requests, read and write the chat table, invoke the chat model and itself, read the service clients and the Anthropic key secrets. |
| Run by | PRD-001 |

## Up the thread

From this running unit to the reason it exists: the SBB it realises names the technologies, the ABBs those realise are inside the contexts it composes, the contexts realise the capabilities, and the capabilities serve the outcomes of PL-001. Every link exists in this catalogue; the registers answer the queries in both directions.

## Findings against the continuum

| Finding | Rule | Where it is addressed |
|---|---|---|
| One Lambda serves BC-006, the index of BC-004 and the fallback loop of BC-005 | A service serves one bounded context | CN-006: the index-backed routes belong with the tools; the fallback loop retires when the Runtime is on |
| Two front ends send different tokens | One contract | The explorer page under portal/ sends the ID token; the chat page the access token; the explorer is not deployed by the module |

