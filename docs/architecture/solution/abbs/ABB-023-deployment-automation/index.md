---
kind: abb
id: ABB-023
title: "ABB-023 Deployment automation"
short_name: "DEPLOY"
description: "One module with nine submodules, applied twice, with the images built inside the account from the deployed source, a CloudFormation entry point that runs the same Terraform, and a release tag a consumer pins."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Platform services"
part_of: BC-008
realises_capabilities: [CAP-013]
realised_by: [SBB-009, SBB-010, SBB-013]
requires: []
domains: [technology]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "The module inputs (CT-010); the launch stack parameters" }
  - { id: "I2", direction: "out", type: "query", description: "Every node, store and service of a deployment; the outputs" }
  - { id: "I3", direction: "out", type: "query", description: "Two images built in the account from the uploaded source" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "infra/modules/*, infra/stack, infra/launch, infra/bootstrap, examples/deployment, Dockerfile, Dockerfile.agent, .github/workflows", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-023 Deployment automation

| Property | Value |
|---|---|
| ABB ID | ABB-023 |
| ABB Name | Deployment automation |
| Short Name | DEPLOY |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Platform services |
| Bounded context | BC-008 |
| Realises | CAP-013 |
| Realised by | SBB-009, SBB-010, SBB-013 |

One module with nine submodules, applied twice, with the images built inside the account from the deployed source, a CloudFormation entry point that runs the same Terraform, and a release tag a consumer pins.

## 1  Purpose

Adoption is an afternoon when the deployment is one module with defaults, buildable from inside the account, and upgradable by moving a tag.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Module.** knowledge-store wiring lake, image-build, network, pipeline, knowledge-graph, knowledge-base, identity, portal, agent; a budget
- **Image build.** A content-hashed source zip; CodeBuild on upload; two ECR repositories
- **Launch stack.** A CodeBuild deployer running Terraform from a custom resource
- **Tests.** Mocked Terraform tests; cfn-lint; the deployment template validated against the local module
- **Release.** Release Please tags; the module pinned by ref

### 2.3  Attributes

- **Self-containment.** Nothing pulled from outside but the pinned base image
- **Reversibility.** Destroy removes everything; the lake kept unless told otherwise

### 2.4  Semantic

Inside: provisioning and building. Outside: what runs.

### 2.5  Identity & Access Management

A role per unit with least privilege; a permissions boundary on every role when given; the deployer role is administrator by design and must be restricted in the account.

### 2.6  Observability

Build logs; the deploy project's log; outputs.

### 2.7  Governance & Policy Enforcement

Branch protection and CI on the repository; the lab follows a pinned release.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | config | The module inputs (CT-010); the launch stack parameters |
| I2 | out | infrastructure | Every node, store and service of a deployment; the outputs |
| I3 | out | artefact | Two images built in the account from the uploaded source |

### 3.4  Capability dependencies (requires)

None beyond the cross-cutting trio.

## 4  Mapping

| Where | What |
|---|---|
| Code | `infra/modules/*, infra/stack, infra/launch, infra/bootstrap, examples/deployment, Dockerfile, Dockerfile.agent, .github/workflows` |
| Capabilities | CAP-013 |
| Context | BC-008 |

## 5  Solution Building Block guidance

Realised by CodeBuild and ECR (SBB-009) and the module with the launch stack (SBB-010); locally the CLI (SBB-013).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
