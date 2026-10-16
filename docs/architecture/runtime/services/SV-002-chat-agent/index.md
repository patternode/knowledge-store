---
kind: service
id: chat-agent
numeric_id: SV-002
title: "SV-002 Chat agent"
description: "The agent on AgentCore Runtime: admits the caller, prompts with the ontology, runs the tool loop under the valves, re-reads and checks every citation, repairs once, applies the guardrail, renders or abstains, and streams its steps."
version: 0.1.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [SBB-006]
part_of: BC-005
composes_contexts: [BC-005, BC-004]
runtime_type: container
repo: { url: "https://github.com/patternode/knowledge-store", path: "." }
module_path: "src/knowledge_store/agent/app.py"
packages: ["knowledge_store.agent", "knowledge_store.workbench", "knowledge_store.tools (local mode only)"]
deployed_to: [DN-005]
run_by: "PRD-001; invoked by the portal as the person"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SV-002 Chat agent

The agent on AgentCore Runtime: admits the caller, prompts with the ontology, runs the tool loop under the valves, re-reads and checks every citation, repairs once, applies the guardrail, renders or abstains, and streams its steps.

| Field | Value |
|---|---|
| Identifier | SV-002, slug `chat-agent` |
| Kind | Service, container |
| Context | BC-005; composes BC-005, BC-004 as built |
| Realises | SBB-006 |
| Node | DN-005 |
| Code | `src/knowledge_store/agent/app.py (entry: python -m knowledge_store.agent.app, port 8080, /invocations)` |
| Talks to | The Gateway over MCP with the caller's token; Bedrock models and the guardrail; the chat table for its daily count. |
| Stores | Writes agent# keys of the chat table only. |
| Role | <name>-agent-runtime: pull its image, invoke the agent model, apply the guardrail, update agent# items, logs, traces, metrics. |
| Run by | PRD-001; invoked by the portal as the person |

## Up the thread

From this running unit to the reason it exists: the SBB it realises names the technologies, the ABBs those realise are inside the contexts it composes, the contexts realise the capabilities, and the capabilities serve the outcomes of PL-001. Every link exists in this catalogue; the registers answer the queries in both directions.

## Findings against the continuum

| Finding | Rule | Where it is addressed |
|---|---|---|
| The agent image also carries the tools in process for local runs | Context integrity | By design for SBB-013; in the deployment the tools are behind the Gateway |

