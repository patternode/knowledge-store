---
kind: outcome
id: OC-003
title: "OC-003 A store the organisation runs itself, at a cost it can see"
description: "One stack in the organisation's own account, no data leaving it, idle cost close to nothing, and valves on every way to spend."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
kpi: "Monthly cost while idle, and the accounts and stacks a deployment needs"
kpi_target: { value: "close to nothing idle apart from the graph instance; one account, one stack", unit: "USD per month; count", measurement: "the cost table in RA-001; the module's inputs" }
business_rationale: "A knowledge store that needs a platform team to run, or that sends documents to a vendor, is not one an organisation adopts for its own material. Self-contained deployment and visible, valved spend are what make the store adoptable."
time_horizon: short
measures:
  - { id: OC-003-M1, measure: "Idle monthly cost of a deployment with the default inputs", target: "about the graph instance alone, or near zero with knowledge_graph.enabled false", unit: "USD per month" }
  - { id: OC-003-M2, measure: "Data that leaves the account during ingestion and answering", target: 0, unit: "bytes, apart from Bedrock calls inside the account's region" }
  - { id: OC-003-M3, measure: "Spend paths without a valve (per question, per person per day, per deployment per month)", target: 0, unit: "paths" }
owned_by_platform: PL-001
requires_capabilities: [CAP-009, CAP-010, CAP-013]
realised_by_use_cases: [UC-002, UC-008, UC-009]
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# OC-003 A store the organisation runs itself, at a cost it can see

| Property | Value |
|---|---|
| Outcome ID | OC-003 |
| Measure | Idle monthly cost; accounts and stacks per deployment |
| Owned by | PL-001 Knowledge Store |

## Definition

A deployment is one Terraform module applied in one AWS account, with the images built inside that account from the deployed source. Model calls go to Bedrock in the account's region, or to the Anthropic API when the operator chooses. Nothing listens without a verified token. Every way to spend has a limit: tool and model calls per question, questions per person per day, answers running at once, and a monthly budget alert.

## Business rationale

Cost and custody are the two reasons an organisation does not deploy a knowledge tool over its own documents. The store answers both structurally rather than by policy: the pay-per-use services idle at nothing, the one fixed cost (the graph instance) can be switched off, and the valves are inputs of the module rather than operational discipline.

## Traceability

Requires CAP-009 access by scope, CAP-010 cost control and CAP-013 self-contained deployment. Realised by UC-008 sign in and read within scope and UC-009 deploy the store.
