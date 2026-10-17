---
kind: abb
id: ABB-023
title: "ABB-023 Image build"
short_name: "BUILD"
description: "The images the store runs, built inside the account from the deployed source so that nothing runs that was not built from what was applied: a content-hashed source, a build per image, and the repositories the task and the runtime pull from. The Terraform module and the CloudFormation launch stack that provision every unit are the deployment mechanism, described with the platform and REF-001, and not a building block."
version: 0.2.0
status: draft
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Platform services"
part_of: BC-008
realises_capabilities: [CAP-013]
realised_by: [SBB-009]
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

# ABB-023 Image build

| Property | Value |
|---|---|
| ABB ID | ABB-023 |
| ABB Name | Image build |
| Short Name | BUILD |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Platform services |
| Bounded context | BC-008 |
| Realises | CAP-013 |
| Realised by | SBB-009 |

The images the store runs, built inside the account from the deployed source so that nothing runs that was not built from what was applied: a content-hashed source, a build per image, and the repositories the task and the runtime pull from. The Terraform module and the CloudFormation launch stack that provision every unit are the deployment mechanism, described with the platform and REF-001, and not a building block.

## 1  Purpose

Adoption is an afternoon when the deployment is one module with defaults, buildable from inside the account, and upgradable by moving a tag.

## 2  Building block

### 2.1  Component Diagram

The components below are what runs inside this one container, listed per the building block calibration standard: none of them is a building block of its own. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Source.** A content-hashed zip of the repository uploaded on apply; an unchanged source never rebuilds
- **Projects.** One build per image, started by an object-created rule; the pipeline image for x86_64, the agent image for arm64
- **Repositories.** Two repositories scanned on push, the last ten images kept, :latest and a hash tag
- **Release.** Release Please tags the repository; a deployment pins the module by tag, and the build follows the pinned source

### 2.3  Attributes

- **Self-containment.** Nothing pulled from outside but the pinned base image
- **Reversibility.** Destroy removes everything; the lake kept unless told otherwise

### 2.4  Semantic

Inside: building and holding images. Outside: provisioning (the module, its roots, the launch stack and the budget), which is not a container, and the units that pull the images.

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
| Code | `infra/modules/image-build; Dockerfile, Dockerfile.agent; .github/workflows; the module and the launch stack in infra/modules/knowledge-store, infra/stack, infra/launch` |
| Capabilities | CAP-013 |
| Context | BC-008 |

## 5  Solution Building Block guidance

Realised by CodeBuild and ECR (SBB-009). The module, its roots, the launch stack and the budget are described in the deployment guide and on REF-001's deployment view; SBB-010 is retired because an infrastructure-as-code module provisions containers and is not one.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.2.0 | 2026-10-17 | Recalibrated to container grain: the block is the image build; the Terraform module and launch stack are provisioning, not a block; renamed from Deployment automation |
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
