---
kind: sbb
id: SBB-019
title: "SBB-019 Evaluation runner on Python"
description: "The evaluation runner as a command in the same package, run by an evaluator against a lake or a deployed chat."
version: 0.3.0
status: active
created: 2026-10-16
last_modified: 2026-10-22
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-021]
realised_by_services: [evaluation-runner]
products:
  - { name: "Python 3.12", vendor: "PSF", licensing: "PSF licence" }
  - { name: "DeepEval 4.3.1", vendor: "Confident AI", licensing: "Apache-2.0" }
product_mapping:
  - { abb_component: "Set loader and scorer", sbb_product: "evaluation/domain/score.py and run.py in the package" }
  - { abb_component: "Targets", sbb_product: "In process against a folder lake, or POST /api/chat with a person's token" }
  - { abb_component: "Grader", sbb_product: "DeepEval G-Eval and faithfulness through the platform's model client (evaluation/adapters/deepeval_grader.py)" }
  - { abb_component: "Run record", sbb_product: "A DeepEval test run (evaluation/adapters/deepeval_runner.py)" }
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
| Products | Python 3.12, DeepEval 4.3.1 (the evals extra) |
| Cloud | none, self-hosted |
| Status | active, as deployed at 0.3.0, recalibrated to container grain |

The evaluation runner as a command in the same package, run by an evaluator against a lake or a deployed chat.

## 1  Purpose

A command, not a service: evaluation is run by a person before a release, and its report is the artefact.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Set loader and scorer | evaluation/domain/score.py and run.py in the package |
| Targets | In process against a folder lake, or POST /api/chat with a person's token |
| Grader | DeepEval G-Eval and faithfulness through the platform's model client (evaluation/adapters/deepeval_grader.py) |
| Run record | A DeepEval test run (evaluation/adapters/deepeval_runner.py) |

## 3  Operation

knowledge-store evals run <set>; a cost estimate before the run. `--runner deepeval` records the run as a DeepEval test run, and `--grader deepeval --judge-model <id>` adds the grader. DeepEval's telemetry is off, and nothing goes to Confident AI without `--upload-to-confident`.

## 4  Cost

The questions asked, and with the grader about five judge calls a question.

## 5  ABB traceability

ABB-021. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the reference architecture that composes this block with the others is RA-001.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain; new in the calibration |
| 0.3.0 | 2026-10-22 | DeepEval as the runner and the grader, replacing Inspect AI (ADR-013) |
