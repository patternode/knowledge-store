---
kind: capability
id: CAP-012
title: "CAP-012 Answer transparency and curation feedback"
description: "Showing how an answer was found and what it cost, which ontology terms questions ask for, read and cite, and what it would take to answer a question the store could not, kept as a request the next ontology version can take."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
level: L2
parent: CAP-001
components:
  organisation: "Curators own the requests; readers see the steps"
  people: ["Curators", "Readers"]
  processes:
    - "Record each model call, tool call, check, repair and guardrail step; stream them"
    - "Count terms queried, read and cited, per collection, all time and per month"
    - "Run the analyst on a question and keep its report as an ontology request"
    - "Feed requests into the candidate register"
  technology: "The workbench recorder and hooks, DynamoDB usage counters, the gap report schema, requests in the lake, the ontology page overlay"
maturity:
  current: 3
  target: 4
  assessment_date: 2026-10-16
  assessor: "Patternode (Dermot O'Brien), reversed from the implementation"
subdomain_kind: core
provided_by_platform: PL-001
realised_by_abbs: [ABB-004, ABB-014, ABB-018]
gaps:
  - "Usage keeps term names, never questions, so a curator sees demand but not the asks behind it"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# CAP-012 Answer transparency and curation feedback

| Property | Value |
|---|---|
| Capability ID | CAP-012 |
| Level | L2 |
| Parent | CAP-001 |
| Status | Draft, reversed from the implementation at 0.3.0 |
| Subdomain | core |
| Maturity | 3, target 4 |
| Realised by | ABB-004, ABB-014, ABB-018 |

Showing how an answer was found and what it cost, which ontology terms questions ask for, read and cite, and what it would take to answer a question the store could not, kept as a request the next ontology version can take.

## 1  Purpose

A curator cannot improve an ontology they cannot see used. The workbench streams the agent's steps, prices them, counts term usage per collection and month, and turns a failed question into a gap report that becomes an ontology request, closing the loop to the next version.

## 2  Capability definition

| Dimension | For Knowledge Store |
|---|---|
| Organisation | Curators own the requests; readers see the steps |
| People | Curators, Readers |
| Processes | Record each model call, tool call, check, repair and guardrail step; stream them; Count terms queried, read and cited, per collection, all time and per month; Run the analyst on a question and keep its report as an ontology request; Feed requests into the candidate register |
| Technology | The workbench recorder and hooks, DynamoDB usage counters, the gap report schema, requests in the lake, the ontology page overlay |

## 3  Sub-capabilities

| Sub-capability | What it covers | Status |
|---|---|---|
| Steps and cost | Streamed and priced per question | In place |
| Term usage | Queried, read, cited counters | In place |
| Gap analysis | The analyst's verdict and proposed terms | In place |
| Ontology requests | Kept reports feeding the next version | In place |

## 4  What the implementation does today

Steps, cost, ontology terms and session totals in the chat page's workbench; a question overlay on the ontology graph; "What would it take?" as a second mode of the same agent.

## 5  Maturity

Current maturity is 3 on the 0 to 5 scale, read from the implementation: the capability is defined, built and in service in the Patternode lab and in any deployment of the module. Target 4.

## 6  Gaps

- Usage keeps term names, never questions, so a curator sees demand but not the asks behind it
