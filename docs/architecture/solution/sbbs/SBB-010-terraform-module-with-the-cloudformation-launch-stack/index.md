---
kind: sbb
id: SBB-010
title: "SBB-010 Terraform module with the CloudFormation launch stack"
description: "The deployment as one module a consumer pins by release tag, and a CloudFormation stack for those without Terraform."
version: 0.1.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-023]
realised_by_services: []
products:
  - { name: "HashiCorp Terraform 1.14", vendor: "HashiCorp", licensing: "BUSL, free to use" }
  - { name: "AWS CloudFormation", vendor: "AWS", licensing: "free" }
  - { name: "AWS Budgets", vendor: "AWS", licensing: "free" }
product_mapping:
  - { abb_component: "Module", sbb_product: "infra/modules/knowledge-store and nine submodules; inputs (CT-010); outputs; mocked tests" }
  - { abb_component: "Roots", sbb_product: "infra/stack as the reference; examples/deployment as a template pinned to a tag" }
  - { abb_component: "Launch stack", sbb_product: "A CodeBuild deployer with administrator rights running the same Terraform from a custom resource, with a state bucket" }
  - { abb_component: "Budget", sbb_product: "A monthly cost budget mailed at 80 percent actual and 100 percent forecast" }
cloud_provider: aws
deployment_model: self-hosted
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-010 Terraform module with the CloudFormation launch stack

| Property | Value |
|---|---|
| SBB ID | SBB-010 |
| Realises | ABB-023 |
| Realised by services | none: provisioning, not a running unit |
| Products | HashiCorp Terraform 1.14; AWS CloudFormation; AWS Budgets |
| Cloud | aws, self-hosted |
| Status | active, as deployed at 0.3.0 |

The deployment as one module a consumer pins by release tag, and a CloudFormation stack for those without Terraform.

## 1  Purpose

One module keeps every connection in one readable file; the launch stack lowers the bar to a form with parameters.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Module | infra/modules/knowledge-store and nine submodules; inputs (CT-010); outputs; mocked tests |
| Roots | infra/stack as the reference; examples/deployment as a template pinned to a tag |
| Launch stack | A CodeBuild deployer with administrator rights running the same Terraform from a custom resource, with a state bucket |
| Budget | A monthly cost budget mailed at 80 percent actual and 100 percent forecast |

## 3  Operation

Two applies; moved blocks when resources move; the deployer and its starter are administrator-equivalent and must be restricted.

## 4  Cost

None beyond what it creates.

## 5  ABB traceability

ABB-023. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the physical pattern that composes this block with the others is REF-001.
