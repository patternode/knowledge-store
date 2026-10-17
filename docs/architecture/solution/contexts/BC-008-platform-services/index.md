---
kind: bounded-context
id: BC-008
title: "BC-008 Platform services"
description: "Model access, the cost ledger, the command line and deployment: the generic services every other context uses and none owns."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
part_of: PL-001
contains: [ABB-028]
realises_capabilities: [CAP-010, CAP-013]
subdomain_kind: generic
c4_levels: [container, component]
ubiquitous_language:
  - { term: "Provider", definition: "bedrock or anthropic, chosen by configuration; every caller speaks the Converse shape" }
  - { term: "Ledger row", definition: "One model call: tokens, list-price cost, latency, outcome, job and run" }
  - { term: "Module", definition: "infra/modules/knowledge-store, the unit a consumer pins by tag" }
  - { term: "Submodule", definition: "lake, image-build, network, pipeline, knowledge-graph, knowledge-base, identity, portal, agent" }
  - { term: "Two applies", definition: "The first creates everything but the agent Runtime; the second switches it on once its image is built" }
  - { term: "Launch stack", definition: "The CloudFormation stack that runs the same Terraform from CodeBuild" }
relationships:
  - { with: BC-001, pattern: open-host-service, role: upstream }
  - { with: BC-005, pattern: open-host-service, role: upstream }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# BC-008 Platform services

| Property | Value |
|---|---|
| Context ID | BC-008 |
| Platform | PL-001 Knowledge Store |
| Owner team | Patternode (Dermot O'Brien) |
| Subdomain | generic |
| Realises | CAP-010, CAP-013 |
| Contains | ABB-028 |

Model access, the cost ledger, the command line and deployment: the generic services every other context uses and none owns.

## Ubiquitous language

| Term | Meaning in this context |
|---|---|
| Provider | bedrock or anthropic, chosen by configuration; every caller speaks the Converse shape |
| Ledger row | One model call: tokens, list-price cost, latency, outcome, job and run |
| Module | infra/modules/knowledge-store, the unit a consumer pins by tag |
| Submodule | lake, image-build, network, pipeline, knowledge-graph, knowledge-base, identity, portal, agent |
| Two applies | The first creates everything but the agent Runtime; the second switches it on once its image is built |
| Launch stack | The CloudFormation stack that runs the same Terraform from CodeBuild |

## Where the model lives today

- `llm.py, ledger.py (one Converse-shaped client over Bedrock or the Anthropic API, with every call priced into the ledger)`
- `cli.py (the knowledge-store command), sparql_lock.py`
- `infra/ (the Terraform module and its submodules, the stack, the launch stack, the bootstrap), Dockerfile, Dockerfile.agent, scripts/`

The shared kernel in all but name: llm.py and ledger.py are imported by ingestion, extraction, answering and the portal. Deployment is Terraform with mocked tests and a CloudFormation entry point.

## Relationships with other contexts

| With | Pattern | Role | Why |
|---|---|---|---|
| BC-001 | open-host-service | upstream | The model client and the lake port |
| BC-005 | open-host-service | upstream | The model client and prices |

## Building blocks

ABB-028 Command line, a page under [../abbs](../../abbs/README.md). The model client is a component of the containers that call models; the Terraform module and the image build are not blocks under the calibration standard (CT-010, DN-003, DN-013).
