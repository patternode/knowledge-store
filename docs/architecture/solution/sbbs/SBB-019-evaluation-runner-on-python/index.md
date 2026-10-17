---
kind: sbb
id: SBB-019
title: "SBB-019 Evaluation runner on Python"
description: "The evaluation runner as a command in the same package, run by an evaluator against a lake or a deployed chat."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-021]
realised_by_services: [evaluation-runner]
products:
  - { name: "Python 3.12", vendor: "PSF", licensing: "PSF licence" }
product_mapping:
  - { abb_component: "Set loader and scorer", sbb_product: "evals/score.py and run.py in the package" }
  - { abb_component: "Targets", sbb_product: "In process against a folder lake, or POST /api/chat with a person's token" }
cloud_provider: none
deployment_model: self-hosted
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-019 Evaluation runner on Python

| Property | Value |
|---|---|
| SBB ID | SBB-019 |
| Realises | ABB-021 |
| Realised by services | evaluation-runner |
| Products | Python 3.12 |
| Cloud | none, self-hosted |
| Status | active, as deployed at 0.3.0, recalibrated to container grain |

The evaluation runner as a command in the same package, run by an evaluator against a lake or a deployed chat.

## 1  Purpose

A command, not a service: evaluation is run by a person before a release, and its report is the artefact.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Set loader and scorer | evals/score.py and run.py in the package |
| Targets | In process against a folder lake, or POST /api/chat with a person's token |

## 3  Operation

knowledge-store evals run <set>; a cost estimate before the run.

## 4  Cost

The questions asked.

## 5  ABB traceability

ABB-021. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the reference architecture that composes this block with the others is RA-001.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain; new in the calibration |
