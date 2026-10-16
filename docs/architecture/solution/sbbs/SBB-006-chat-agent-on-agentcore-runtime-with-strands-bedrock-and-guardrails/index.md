---
kind: sbb
id: SBB-006
title: "SBB-006 Chat agent on AgentCore Runtime with Strands, Bedrock and Guardrails"
description: "The answering agent as a container on AgentCore Runtime, acting only as its caller, with the checks and the guardrail in the same process."
version: 0.1.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-014, ABB-015, ABB-016, ABB-017]
realised_by_services: [chat-agent]
products:
  - { name: "Amazon Bedrock AgentCore Runtime", vendor: "AWS", licensing: "pay per use" }
  - { name: "Strands Agents", vendor: "AWS (open source)", licensing: "Apache-2.0" }
  - { name: "Amazon Bedrock models (Claude)", vendor: "AWS and Anthropic", licensing: "per token" }
  - { name: "Amazon Bedrock Guardrails", vendor: "AWS", licensing: "per text unit" }
product_mapping:
  - { abb_component: "Runtime", sbb_product: "An arm64 container built in the account, a Cognito JWT authoriser, idle timeout two hours, an optional prod endpoint pinned to a version" }
  - { abb_component: "Agent", sbb_product: "Strands with BedrockModel, hooks for the valves and the recorder, structured output for claims" }
  - { abb_component: "Checks", sbb_product: "grounding.py in the image; the guardrail applied by ApplyGuardrail with contextual grounding" }
  - { abb_component: "Streaming", sbb_product: "Server-sent events of steps then the result" }
cloud_provider: aws
deployment_model: managed
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-006 Chat agent on AgentCore Runtime with Strands, Bedrock and Guardrails

| Property | Value |
|---|---|
| SBB ID | SBB-006 |
| Realises | ABB-014, ABB-015, ABB-016, ABB-017 |
| Realised by services | chat-agent |
| Products | Amazon Bedrock AgentCore Runtime; Strands Agents; Amazon Bedrock models (Claude); Amazon Bedrock Guardrails |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0 |

The answering agent as a container on AgentCore Runtime, acting only as its caller, with the checks and the guardrail in the same process.

## 1  Purpose

The Runtime gives per-session isolation, a JWT authoriser and streaming without a server to run; Strands gives hooks where the valves bite; Guardrails gives contextual grounding as a service.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Runtime | An arm64 container built in the account, a Cognito JWT authoriser, idle timeout two hours, an optional prod endpoint pinned to a version |
| Agent | Strands with BedrockModel, hooks for the valves and the recorder, structured output for claims |
| Checks | grounding.py in the image; the guardrail applied by ApplyGuardrail with contextual grounding |
| Streaming | Server-sent events of steps then the result |

## 3  Operation

Created on the second apply once the image exists; prod_version pins an endpoint; the Runtime's log group is not managed by Terraform.

## 4  Cost

Per invocation second plus model tokens; the model is the cost that matters.

## 5  ABB traceability

ABB-014, ABB-015, ABB-016, ABB-017. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the physical pattern that composes this block with the others is REF-001.
