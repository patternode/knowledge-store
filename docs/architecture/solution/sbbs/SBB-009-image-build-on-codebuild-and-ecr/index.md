---
kind: sbb
id: SBB-009
title: "SBB-009 Image build on CodeBuild and ECR"
description: "Both images built inside the account from the deployed source, so nothing runs that was not built from what was applied."
version: 0.1.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-023]
realised_by_services: [pipeline, chat-agent]
products:
  - { name: "AWS CodeBuild", vendor: "AWS", licensing: "per build minute" }
  - { name: "Amazon ECR", vendor: "AWS", licensing: "storage" }
  - { name: "Python 3.12 slim base image from ECR Public", vendor: "AWS", licensing: "pinned by digest" }
product_mapping:
  - { abb_component: "Source", sbb_product: "A content-hashed zip of the repository uploaded by Terraform; an unchanged source never rebuilds" }
  - { abb_component: "Projects", sbb_product: "<name>-image (x86_64) and <name>-agent-image (arm64), started by an object-created rule" }
  - { abb_component: "Repositories", sbb_product: "<name>-pipeline and <name>-agent, scanned on push, the last ten kept, :latest and a hash tag" }
cloud_provider: aws
deployment_model: managed
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-009 Image build on CodeBuild and ECR

| Property | Value |
|---|---|
| SBB ID | SBB-009 |
| Realises | ABB-023 |
| Realised by services | pipeline, chat-agent |
| Products | AWS CodeBuild; Amazon ECR; Python 3.12 slim base image from ECR Public |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0 |

Both images built inside the account from the deployed source, so nothing runs that was not built from what was applied.

## 1  Purpose

Supply chain: the only outside pull is a base image pinned by digest. Builds on upload make the first apply self-sufficient.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Source | A content-hashed zip of the repository uploaded by Terraform; an unchanged source never rebuilds |
| Projects | <name>-image (x86_64) and <name>-agent-image (arm64), started by an object-created rule |
| Repositories | <name>-pipeline and <name>-agent, scanned on push, the last ten kept, :latest and a hash tag |

## 3  Operation

Anything written under the build bucket's source/ starts a privileged build; restrict who may write there.

## 4  Cost

Minutes per build.

## 5  ABB traceability

ABB-023. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the physical pattern that composes this block with the others is REF-001.
