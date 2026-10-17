---
kind: service
id: chat-page
numeric_id: SV-007
title: "SV-007 Chat page"
description: "The static chat and ontology pages served from a private bucket through CloudFront, with no build step and no external scripts."
version: 0.1.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [SBB-007]
part_of: BC-006
composes_contexts: [BC-006]
runtime_type: managed-service
repo: { url: "https://github.com/patternode/knowledge-store", path: "." }
module_path: "chat/"
packages: []
deployed_to: [DN-009]
run_by: "PRD-001"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SV-007 Chat page

The static chat and ontology pages served from a private bucket through CloudFront, with no build step and no external scripts.

| Field | Value |
|---|---|
| Identifier | SV-007, slug `chat-page` |
| Kind | Service, managed-service |
| Context | BC-006; composes BC-006 as built |
| Realises | SBB-007 |
| Node | DN-009 |
| Code | `chat/ (index.html, app.js, common.js, ontology.html, ontology.js, styles.css; config.json and brand.css written by Terraform)` |
| Talks to | The portal API; Cognito's hosted UI; a host website over postMessage in site mode. |
| Stores | sessionStorage and localStorage in the browser. |
| Role | None; CloudFront reads the bucket through origin access control. |
| Run by | PRD-001 |

## Up the thread

From this running unit to the reason it exists: the SBB it realises names the technologies, the ABBs those realise are inside the contexts it composes, the contexts realise the capabilities, and the capabilities serve the outcomes of PL-001. Every link exists in this catalogue; the registers answer the queries in both directions.

## Findings against the continuum

| Finding | Rule | Where it is addressed |
|---|---|---|
| A second page, the explorer under portal/, is in the repository and not deployed | Dead code | Retire or document it; it sends a different token (SV-003) |

