---
kind: pattern
id: REF-001
title: "REF-001 Knowledge Store on AWS"
pattern_type: reference-architecture
pattern_scope: platform
status: active
version: "0.3"
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
author: "Patternode (Dermot O'Brien)"
implements: [PAT-001]
model:
  diagram: components.drawio
realises: [CAP-002, CAP-003, CAP-004, CAP-005, CAP-006, CAP-007, CAP-008, CAP-009, CAP-010, CAP-011, CAP-012, CAP-013]
serves: [UC-001, UC-002, UC-003, UC-004, UC-005, UC-006, UC-007, UC-008, UC-009]
references:
  - { type: cost-model, path: "docs/architecture/aws/aws.md#costs" }
  - { type: evidence, path: "examples/evals" }
  - { type: runbook, path: "docs/deploy/aws/README.md" }
  - { type: doc, path: "docs/architecture/aws/aws.md" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# REF-001 Knowledge Store on AWS

<!-- deck:cover subtitle="The physical pattern: Knowledge Store as one Terraform module on AWS" footnote="Reversed from the implementation at 0.3.0. Draft." -->

The physical pattern: PAT-001 made concrete in solution building blocks on AWS, as the module deploys it. The narrative, the request flow, the grounding table, the valves and the cost table are in [aws/aws.md](../../../aws/aws.md), which this page does not repeat; the components and their Terraform are in [the deployment components guide](../../../../deploy/aws/components.md). This page is the pattern's register form: what blocks, what interfaces, what controls, what decisions, so the catalogue can be walked from a use case to a running unit.

![REF-001 solution building blocks and interfaces](./components.svg)

Generated from the Required Building Blocks and Interfaces tables with the model skill (`components.drawio` is the source). The illustrated reference architecture is [aws/architecture.svg](../../../aws/architecture.svg), from [aws/architecture.drawio](../../../aws/architecture.drawio) and its generator [architecture.py](../../../aws/architecture.py).

<!-- deck:slide label="Context" -->

## Context

One AWS account, one Terraform module, two applies. Ingestion as a Fargate sweep started by uploads; the record in S3; the graph in Neptune; the passage index on S3 Vectors; the tools behind AgentCore Gateway; the agent on AgentCore Runtime with Bedrock models and Guardrails; the page and API on CloudFront, API Gateway, Lambda and DynamoDB; sign-in with Cognito or a host website; images built in the account.

<!-- deck:slide label="Non-goals" -->

### Non-goals

Multi-region, multi-account and a shared tenant model are out of scope: one deployment is one account and one stack.

<!-- deck:slide label="Building blocks" -->

## Required Building Blocks

| Building Block | Realises | Role |
|---|---|---|
| SBB-001 Lake on S3 | ABB-002 | The record |
| SBB-002 Sweep on ECS Fargate with EventBridge, SQS, Pipes and Scheduler | ABB-004 | The sweep and its triggers |
| SBB-014 The pipeline image | ABB-001, ABB-003, ABB-005 to ABB-011 | Every pipeline-side block |
| SBB-003 Knowledge graph on Amazon Neptune | ABB-011 | The SPARQL projection |
| SBB-004 Passage index on Bedrock Knowledge Base with S3 Vectors | ABB-013 | Search by meaning |
| SBB-005 Tools on AgentCore Gateway with Lambda targets and the interceptor | ABB-012, ABB-013, ABB-020 | The fixed tools, scoped |
| SBB-006 Chat agent on AgentCore Runtime with Strands, Bedrock and Guardrails | ABB-014 to ABB-017 | Answering |
| SBB-007 Portal on CloudFront, API Gateway, Lambda and DynamoDB | ABB-018, ABB-019 | The page and the API |
| SBB-008 Identity on Cognito | ABB-020 | People and tokens |
| SBB-009 Image build on CodeBuild and ECR | ABB-023 | Images in the account |
| SBB-010 Terraform module with the CloudFormation launch stack | ABB-023 | The deployment |
| SBB-012 Model access through Bedrock or the Anthropic API | ABB-022 | The model, priced |
| SBB-011 Optional projection backends | ABB-011 | When memory is outgrown |

<!-- deck:slide label="Interfaces" -->

## Interfaces

| Interface | Provider | Consumer | Purpose |
|---|---|---|---|
| IF-01 | SBB-001 Lake on S3 | SBB-002 Sweep on ECS Fargate with EventBridge, SQS, Pipes and Scheduler | upload events; the lake read and written |
| IF-02 | SBB-009 Image build on CodeBuild and ECR | SBB-002 Sweep on ECS Fargate with EventBridge, SQS, Pipes and Scheduler | the pipeline image |
| IF-03 | SBB-002 Sweep on ECS Fargate with EventBridge, SQS, Pipes and Scheduler | SBB-014 The pipeline image: rdflib, pySHACL, pypdf and Claude | runs the sweep |
| IF-04 | SBB-012 Model access through Bedrock or the Anthropic API | SBB-014 The pipeline image: rdflib, pySHACL, pypdf and Claude | discovery and extraction calls |
| IF-05 | SBB-014 The pipeline image: rdflib, pySHACL, pypdf and Claude | SBB-003 Knowledge graph on Amazon Neptune | named graphs loaded |
| IF-06 | SBB-014 The pipeline image: rdflib, pySHACL, pypdf and Claude | SBB-004 Passage index on Bedrock Knowledge Base with S3 Vectors | passages synced; an ingestion job |
| IF-07 | SBB-014 The pipeline image: rdflib, pySHACL, pypdf and Claude | SBB-011 Optional projection backends: Neo4j, Apache AGE and MongoDB | the optional loads |
| IF-08 | SBB-003 Knowledge graph on Amazon Neptune | SBB-005 Tools on AgentCore Gateway with Lambda targets and the interceptor | read-only SPARQL |
| IF-09 | SBB-004 Passage index on Bedrock Knowledge Base with S3 Vectors | SBB-005 Tools on AgentCore Gateway with Lambda targets and the interceptor | Retrieve |
| IF-10 | SBB-005 Tools on AgentCore Gateway with Lambda targets and the interceptor | SBB-006 Chat agent on AgentCore Runtime with Strands, Bedrock and Guardrails | MCP tools as the caller (CT-002, CT-003) |
| IF-11 | SBB-012 Model access through Bedrock or the Anthropic API | SBB-006 Chat agent on AgentCore Runtime with Strands, Bedrock and Guardrails | the agent model and the guardrail |
| IF-12 | SBB-006 Chat agent on AgentCore Runtime with Strands, Bedrock and Guardrails | SBB-007 Portal on CloudFront, API Gateway, Lambda and DynamoDB | invocation as the person; steps streamed (CT-004) |
| IF-13 | SBB-008 Identity on Cognito | SBB-007 Portal on CloudFront, API Gateway, Lambda and DynamoDB | sign-in and tokens (CT-012) |
| IF-14 | SBB-008 Identity on Cognito | SBB-005 Tools on AgentCore Gateway with Lambda targets and the interceptor | the JWT authoriser; the scope written by the interceptor |
| IF-15 | SBB-001 Lake on S3 | SBB-007 Portal on CloudFront, API Gateway, Lambda and DynamoDB | served layers read; requests written; signed links |
| IF-16 | SBB-001 Lake on S3 | SBB-005 Tools on AgentCore Gateway with Lambda targets and the interceptor | gold, silver, ontology and config read |
| IF-17 | SBB-009 Image build on CodeBuild and ECR | SBB-006 Chat agent on AgentCore Runtime with Strands, Bedrock and Guardrails | the agent image |
| IF-18 | SBB-010 Terraform module with the CloudFormation launch stack | SBB-001 Lake on S3 | provisions; writes configuration and tool schemas (CT-010) |

The contracts register, [../../contracts.csv](../../contracts.csv), gives each interface its definition and versioning.

<!-- deck:slide label="Deployment view" -->

## Deployment view

| Service | Node | Store |
|---|---|---|
| SV-001 pipeline | DN-004 Fargate in DN-002 | writes ST-002 to ST-006, ST-008, ST-009, ST-010, ST-015, ST-016 |
| SV-002 chat-agent | DN-005 AgentCore Runtime | ST-011 agent# keys |
| SV-003 portal-api | DN-007 Lambda behind DN-008 and DN-009 | ST-011; reads ST-004, ST-005, ST-003, ST-002 |
| SV-004 tools-graph | DN-007 Lambda in DN-002 behind DN-006 | reads ST-008, ST-004, ST-005 |
| SV-005 tools-passages | DN-007 Lambda behind DN-006 | reads ST-007, ST-003, ST-004 |
| SV-006 agent-interceptor | DN-007 Lambda on DN-006 | none |
| SV-007 chat-page | DN-009 CloudFront from ST-012 | browser storage |

<!-- deck:slide label="Controls" -->

## Controls

Those of PAT-001, plus: the origin secret between CloudFront and the API; reserved concurrency and the API throttle; the web ACL input; IAM authentication and private subnets for Neptune; a role per unit with a permissions boundary; the budget alert; images pinned by digest. The full table is [security.md](../../../security.md).

<!-- deck:slide label="Cost" -->

## Cost

The cost table in [aws/aws.md](../../../aws/aws.md#costs) is the cost model: the Neptune instance is the fixed cost; everything else is per use; model calls are the cost that matters.

<!-- deck:slide label="Decisions" -->

## Decisions

ADR-006 one module built in-account; ADR-007 the passage index on S3 Vectors; ADR-008 memory by default with optional backends; ADR-009 tables bound as snapshots. Open: CN-001 the graph at scale, CN-006 the deployables along the contexts.
