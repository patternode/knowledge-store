---
kind: capability
id: CAP-013
title: "CAP-013 Self-contained deployment and operation"
description: "Deploying the whole store into one account from one Terraform module, with the images built inside that account from the deployed source, a launch stack for those without Terraform, and the branding and network of the deploying organisation."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
level: L2
parent: CAP-001
components:
  organisation: "The administrator applies; the product owner releases the module by tag"
  people: ["Administrators", "The release process"]
  processes:
    - "Apply the module with the organisation's inputs; apply again to switch the agent on"
    - "Build the pipeline and agent images in the account when the source changes"
    - "Pin a release tag and move it to upgrade"
    - "Substitute the name, mark, colours and domain"
    - "Run locally over a folder with no cloud"
  technology: "The Terraform module and its submodules with mocked tests, CodeBuild and ECR, the CloudFormation launch stack, branding inputs, the CLI and the local portal server"
maturity:
  current: 4
  target: 4
  assessment_date: 2026-10-16
  assessor: "Patternode (Dermot O'Brien), reversed from the implementation"
subdomain_kind: generic
provided_by_platform: PL-001
realised_by_abbs: [ABB-028]
gaps:
  - "The launch stack's deploy project runs as administrator, by design, and must be restricted in the account"
  - "Two log groups are outside Terraform and have no retention"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# CAP-013 Self-contained deployment and operation

| Property | Value |
|---|---|
| Capability ID | CAP-013 |
| Level | L2 |
| Parent | CAP-001 |
| Status | Draft, reversed from the implementation at 0.3.0 |
| Subdomain | generic |
| Maturity | 4, target 4 |
| Realised by | ABB-028, for operation; the deployment itself is the Terraform module and the launch stack (CT-010), which are provisioning rather than blocks under the [calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md), on nodes DN-003 and DN-013 |

Deploying the whole store into one account from one Terraform module, with the images built inside that account from the deployed source, a launch stack for those without Terraform, and the branding and network of the deploying organisation.

## 1  Purpose

Adoption depends on the store being someone else's to run. One module, one account, nothing pulled from outside but a pinned base image, a two-stage apply that is documented, and a CloudFormation entry point make a deployment an afternoon rather than a project.

## 2  Capability definition

| Dimension | For Knowledge Store |
|---|---|
| Organisation | The administrator applies; the product owner releases the module by tag |
| People | Administrators, The release process |
| Processes | Apply the module with the organisation's inputs; apply again to switch the agent on; Build the pipeline and agent images in the account when the source changes; Pin a release tag and move it to upgrade; Substitute the name, mark, colours and domain; Run locally over a folder with no cloud |
| Technology | The Terraform module and its submodules with mocked tests, CodeBuild and ECR, the CloudFormation launch stack, branding inputs, the CLI and the local portal server |

## 3  Sub-capabilities

| Sub-capability | What it covers | Status |
|---|---|---|
| One module | Submodules, inputs, outputs, mocked tests | In place |
| In-account image build | CodeBuild from the uploaded source | In place |
| Launch stack | CloudFormation for those without Terraform | In place |
| Branding | Name, mark, colours, domain | In place |
| Local run | A folder lake and the Anthropic API | In place |

## 4  What the implementation does today

Nine submodules under one module; infra/stack as the reference root and examples/deployment as a template pinned to a tag; the launch stack running the same Terraform from CodeBuild; Release Please tagging versions.

## 5  Maturity

Current maturity is 4 on the 0 to 5 scale, read from the implementation: the capability is defined, built and in service in the Patternode lab and in any deployment of the module. Target 4.

## 6  Gaps

- The launch stack's deploy project runs as administrator, by design, and must be restricted in the account
- Two log groups are outside Terraform and have no retention
