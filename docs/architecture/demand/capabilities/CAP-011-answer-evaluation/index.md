---
kind: capability
id: CAP-011
title: "CAP-011 Answer evaluation"
description: "Knowing whether the answers are right, from a set of questions with the facts a right answer states and the documents it should cite, scored deterministically with no model as judge."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
level: L2
parent: CAP-001
components:
  organisation: "The product owner keeps the example sets; a deployment keeps its own"
  people: ["Evaluators", "Curators reading false negatives"]
  processes:
    - "Write a set: question, kind, must, must_not, first, sources, answerable"
    - "Run in-process against a lake or against the deployed chat as a person"
    - "Score and report accuracy, grounded share, source hits, false abstentions and missed abstentions"
  technology: "YAML sets, the runner (python -m knowledge_store.apps.evaluate), deterministic scoring, a markdown and JSON report"
maturity:
  current: 3
  target: 4
  assessment_date: 2026-10-16
  assessor: "Patternode (Dermot O'Brien), reversed from the implementation"
subdomain_kind: supporting
provided_by_platform: PL-001
realised_by_abbs: [ABB-021]
gaps:
  - "Runs are started by hand and cost money per question; nothing runs them on a schedule"
  - "Scores are per run; no history is kept across releases"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# CAP-011 Answer evaluation

| Property | Value |
|---|---|
| Capability ID | CAP-011 |
| Level | L2 |
| Parent | CAP-001 |
| Status | Draft, reversed from the implementation at 0.3.0 |
| Subdomain | supporting |
| Maturity | 3, target 4 |
| Realised by | ABB-021 |

Knowing whether the answers are right, from a set of questions with the facts a right answer states and the documents it should cite, scored deterministically with no model as judge.

## 1  Purpose

A grounded answer can still be wrong or missing. Evaluation sets make the four outcomes countable (true and false positives and negatives), so a release can be compared with the last and a collection's ontology can be seen to lack what a question needs.

## 2  Capability definition

| Dimension | For Knowledge Store |
|---|---|
| Organisation | The product owner keeps the example sets; a deployment keeps its own |
| People | Evaluators, Curators reading false negatives |
| Processes | Write a set: question, kind, must, must_not, first, sources, answerable; Run in-process against a lake or against the deployed chat as a person; Score and report accuracy, grounded share, source hits, false abstentions and missed abstentions |
| Technology | YAML sets, the runner (python -m knowledge_store.apps.evaluate), deterministic scoring, a markdown and JSON report |

## 3  Sub-capabilities

| Sub-capability | What it covers | Status |
|---|---|---|
| Set format | Questions with expected facts and sources | In place |
| Runner | In-process or against the API | In place |
| Deterministic scoring | No model as judge | In place |
| History | Scores across releases | Not started |

## 4  What the implementation does today

Two sets ship: space missions (documents and catalogue tables) and the Sherlock Holmes stories. A run against the API counts against the person's quota.

## 5  Maturity

Current maturity is 3 on the 0 to 5 scale, read from the implementation: the capability is defined, built and in service in the Patternode lab and in any deployment of the module. Target 4.

## 6  Gaps

- Runs are started by hand and cost money per question; nothing runs them on a schedule
- Scores are per run; no history is kept across releases
