---
kind: service
id: evaluation-runner
numeric_id: SV-009
title: "SV-009 Evaluation runner"
description: "Runs an evaluation set against a lake in process or against the deployed chat as a person, scores deterministically and writes the report."
version: 0.1.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [SBB-013]
part_of: BC-007
composes_contexts: [BC-007]
runtime_type: native
repo: { url: "https://github.com/patternode/knowledge-store", path: "." }
module_path: "src/knowledge_store/evals/run.py"
packages: ["knowledge_store.evals"]
deployed_to: [DN-014]
run_by: "evaluators"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SV-009 Evaluation runner

Runs an evaluation set against a lake in process or against the deployed chat as a person, scores deterministically and writes the report.

| Field | Value |
|---|---|
| Identifier | SV-009, slug `evaluation-runner` |
| Kind | Service, native |
| Context | BC-007; composes BC-007 as built |
| Realises | SBB-013 |
| Node | DN-014 |
| Code | `src/knowledge_store/evals/run.py (python -m knowledge_store.evals)` |
| Talks to | The agent in process, or POST /api/chat with a person's token. |
| Stores | build/eval/<name>-<timestamp>/ locally. |
| Role | The evaluator's credentials or token. |
| Run by | evaluators |

## Up the thread

From this running unit to the reason it exists: the SBB it realises names the technologies, the ABBs those realise are inside the contexts it composes, the contexts realise the capabilities, and the capabilities serve the outcomes of PL-001. Every link exists in this catalogue; the registers answer the queries in both directions.

## Findings against the continuum

None.
