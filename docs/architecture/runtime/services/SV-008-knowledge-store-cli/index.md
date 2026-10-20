---
kind: service
id: knowledge-store-cli
numeric_id: SV-008
title: "SV-008 Command line"
description: "Every stage as a command, the ontology lifecycle (pull, diff, publish, activate, render), candidates, status and collections; the pipeline image's entry point and the curator's tool."
version: 0.1.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [SBB-013]
part_of: BC-008
composes_contexts: [BC-001, BC-002, BC-003, BC-004, BC-008]
runtime_type: native
repo: { url: "https://github.com/patternode/knowledge-store", path: "." }
module_path: "src/knowledge_store/apps/cli.py"
packages: ["knowledge_store.apps.cli"]
deployed_to: [DN-004, DN-014]
run_by: "operators and curators"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SV-008 Command line

Every stage as a command, the ontology lifecycle (pull, diff, publish, activate, render), candidates, status and collections; the pipeline image's entry point and the curator's tool.

| Field | Value |
|---|---|
| Identifier | SV-008, slug `knowledge-store-cli` |
| Kind | Service, native |
| Context | BC-008; composes BC-001, BC-002, BC-003, BC-004, BC-008 as built |
| Realises | SBB-013 |
| Node | DN-004, DN-014 |
| Code | `src/knowledge_store/apps/cli.py (console script knowledge-store)` |
| Talks to | The lake and the model; whatever the command needs. |
| Stores | As the command. |
| Role | The operator's credentials, or the pipeline task's in the image. |
| Run by | operators and curators |

## Up the thread

From this running unit to the reason it exists: the SBB it realises names the technologies, the ABBs those realise are inside the contexts it composes, the contexts realise the capabilities, and the capabilities serve the outcomes of PL-001. Every link exists in this catalogue; the registers answer the queries in both directions.

## Findings against the continuum

None.
