---
kind: sbb
id: SBB-006
title: "SBB-006 Chat agent on AgentCore Runtime with Strands, Bedrock and Guardrails"
description: "The answering agent as a container on AgentCore Runtime, acting only as its caller, with the checks, the valves, the guardrail and the recorder in the same process."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-014]
realised_by_services: [chat-agent]
products:
  - { name: "Amazon Bedrock AgentCore Runtime", vendor: "AWS", licensing: "pay per use" }
  - { name: "Strands Agents", vendor: "AWS (open source)", licensing: "Apache-2.0" }
  - { name: "Amazon Bedrock models (Claude)", vendor: "AWS and Anthropic", licensing: "per token" }
  - { name: "Amazon Bedrock Guardrails", vendor: "AWS", licensing: "per text unit" }
product_mapping:
  - { abb_component: "Admission and prompt", sbb_product: "The Runtime's Cognito JWT authoriser; the agent rendition read from the lake" }
  - { abb_component: "Tool loop", sbb_product: "Strands with BedrockModel, hooks for the valves and the recorder, structured output for claims" }
  - { abb_component: "Re-read and repair", sbb_product: "grounding.py in the image, re-reading as the caller through the gateway" }
  - { abb_component: "Guardrail", sbb_product: "ApplyGuardrail with contextual grounding on the question and each claim" }
  - { abb_component: "Valves", sbb_product: "valves.py hooks on tool calls, model calls, output tokens and repairs" }
  - { abb_component: "Recorder and pricing", sbb_product: "Every step with duration, usage and price; the ledger client" }
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
| Realises | ABB-014 |
| Realised by services | chat-agent |
| Products | Amazon Bedrock AgentCore Runtime; Strands Agents; Amazon Bedrock models (Claude); Amazon Bedrock Guardrails |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0, recalibrated to container grain |

The answering agent as a container on AgentCore Runtime, acting only as its caller, with the checks, the valves, the guardrail and the recorder in the same process.

## 1  Purpose

The Runtime gives per-session isolation, a JWT authoriser and streaming without a server to run; Strands gives hooks where the valves bite; Guardrails gives contextual grounding as a service.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Admission and prompt | The Runtime's Cognito JWT authoriser; the agent rendition read from the lake |
| Tool loop | Strands with BedrockModel, hooks for the valves and the recorder, structured output for claims |
| Re-read and repair | grounding.py in the image, re-reading as the caller through the gateway |
| Guardrail | ApplyGuardrail with contextual grounding on the question and each claim |
| Valves | valves.py hooks on tool calls, model calls, output tokens and repairs |
| Recorder and pricing | Every step with duration, usage and price; the ledger client |
| Streaming | Server-sent events of steps then the result |

## 3  Operation

Created on the second apply once the image exists (ST-017); prod_version pins an endpoint; agent.runtime false leaves the Chat API's fallback loop answering; the Runtime's log group is not managed by Terraform.

## 4  Cost

Per invocation second plus model and guardrail calls.

## 5  ABB traceability

ABB-014. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the reference architecture that composes this block with the others is RA-001.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain |
