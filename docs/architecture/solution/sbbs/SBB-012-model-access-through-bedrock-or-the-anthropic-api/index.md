---
kind: sbb
id: SBB-012
title: "SBB-012 Model access through Bedrock or the Anthropic API"
description: "Claude through Bedrock in the account's region, so no data leaves the account, or through the Anthropic API when the operator chooses."
version: 0.1.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-022, ABB-005, ABB-009, ABB-014]
realised_by_services: [pipeline, chat-agent, portal-api]
products:
  - { name: "Amazon Bedrock (Claude models, inference profiles)", vendor: "AWS and Anthropic", licensing: "per token" }
  - { name: "Anthropic API", vendor: "Anthropic", licensing: "per token" }
product_mapping:
  - { abb_component: "Client", sbb_product: "runtime_client returns a Converse client over bedrock-runtime or an adapter over the Messages API; every call wrapped by the ledger" }
  - { abb_component: "Configuration", sbb_product: "llm_provider, extraction_model_id, chat_model_id, agent.model_id; the Anthropic key from Secrets Manager" }
  - { abb_component: "Grants", sbb_product: "Model invocation scoped to the configured model id and its foundation model" }
cloud_provider: multi
deployment_model: managed
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-012 Model access through Bedrock or the Anthropic API

| Property | Value |
|---|---|
| SBB ID | SBB-012 |
| Realises | ABB-022, ABB-005, ABB-009, ABB-014 |
| Realised by services | pipeline, chat-agent, portal-api |
| Products | Amazon Bedrock (Claude models, inference profiles); Anthropic API |
| Cloud | multi, managed |
| Status | active, as deployed at 0.3.0 |

Claude through Bedrock in the account's region, so no data leaves the account, or through the Anthropic API when the operator chooses.

## 1  Purpose

Bedrock keeps documents in the account and bills on the same account; the Anthropic API is the local and the fallback path. One client makes the choice configuration.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Client | runtime_client returns a Converse client over bedrock-runtime or an adapter over the Messages API; every call wrapped by the ledger |
| Configuration | llm_provider, extraction_model_id, chat_model_id, agent.model_id; the Anthropic key from Secrets Manager |
| Grants | Model invocation scoped to the configured model id and its foundation model |

## 3  Operation

Grant model access in the account before applying; regional inference profiles add ten percent, which the ledger records.

## 4  Cost

The cost that matters: discovery, extraction and each question.

## 5  ABB traceability

ABB-022, ABB-005, ABB-009, ABB-014. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the physical pattern that composes this block with the others is REF-001.
