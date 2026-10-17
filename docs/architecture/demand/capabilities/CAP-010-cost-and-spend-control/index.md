---
kind: capability
id: CAP-010
title: "CAP-010 Cost and spend control"
description: "Bounding what a question, a person, a day and a month can cost, pricing every model call, and keeping the idle cost of a deployment close to nothing."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
level: L2
parent: CAP-001
components:
  organisation: "The administrator sets the valves and the budget; the product owner sets the defaults"
  people: ["Administrators", "Curators reading cost in the workbench"]
  processes:
    - "Limit tool calls, model calls and output tokens per question; repairs; checked figures"
    - "Count questions per person per day at the portal and invocations at the agent"
    - "Cap concurrent answers with reserved concurrency; throttle the API"
    - "Price each model call and write the ledger; show the cost of a question"
    - "Alert at 80 percent of a monthly budget"
  technology: "Environment valves read by Strands hooks, DynamoDB conditional writes, Lambda reserved concurrency, API Gateway throttling, the ledger in the lake, AWS Budgets"
maturity:
  current: 4
  target: 4
  assessment_date: 2026-10-16
  assessor: "Patternode (Dermot O'Brien), reversed from the implementation"
subdomain_kind: supporting
provided_by_platform: PL-001
realised_by_abbs: [ABB-014, ABB-019, ABB-028]
gaps:
  - "Guardrail and tool calls are not priced"
  - "The budget is an alert, not a stop"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# CAP-010 Cost and spend control

| Property | Value |
|---|---|
| Capability ID | CAP-010 |
| Level | L2 |
| Parent | CAP-001 |
| Status | Draft, reversed from the implementation at 0.3.0 |
| Subdomain | supporting |
| Maturity | 4, target 4 |
| Realised by | ABB-014, ABB-019, ABB-028 |

Bounding what a question, a person, a day and a month can cost, pricing every model call, and keeping the idle cost of a deployment close to nothing.

## 1  Purpose

Spend is the thing that stops a knowledge tool being left on. Every way to spend has a valve set at deployment, every model call is priced into a ledger, and the architecture idles at nothing apart from the graph instance, which can be switched off.

## 2  Capability definition

| Dimension | For Knowledge Store |
|---|---|
| Organisation | The administrator sets the valves and the budget; the product owner sets the defaults |
| People | Administrators, Curators reading cost in the workbench |
| Processes | Limit tool calls, model calls and output tokens per question; repairs; checked figures; Count questions per person per day at the portal and invocations at the agent; Cap concurrent answers with reserved concurrency; throttle the API; Price each model call and write the ledger; show the cost of a question; Alert at 80 percent of a monthly budget |
| Technology | Environment valves read by Strands hooks, DynamoDB conditional writes, Lambda reserved concurrency, API Gateway throttling, the ledger in the lake, AWS Budgets |

## 3  Sub-capabilities

| Sub-capability | What it covers | Status |
|---|---|---|
| Per-question valves | Hooks that cancel a call past its budget | In place |
| Per-person quotas | Portal and agent daily counts | In place |
| Concurrency and throttling | Reserved concurrency, API throttle | In place |
| Metering | A priced ledger row per call | In place |
| Budget | Monthly alert | In place |

## 4  What the implementation does today

Sixteen tool calls, fourteen model calls, 4,000 output tokens and one repair per question; thirty questions per person per day; twenty answers at once; a ledger row per Converse call with list-price cost.

## 5  Maturity

Current maturity is 4 on the 0 to 5 scale, read from the implementation: the capability is defined, built and in service in the Patternode lab and in any deployment of the module. Target 4.

## 6  Gaps

- Guardrail and tool calls are not priced
- The budget is an alert, not a stop
