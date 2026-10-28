---
kind: outcome
id: OC-001
title: "OC-001 Answers a reader can check"
description: "No statement reaches a reader without a source they may open and a check that the words are there."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
kpi: "Share of shown statements that passed the citation and grounding checks"
kpi_target: { value: 100, unit: "percent", measurement: "by construction in ABB-014; false positives counted by CAP-011 evaluation runs" }
business_rationale: "An answer nobody can check is worth less than the documents it came from. The store exists to make an organisation's own writing answerable without adding a layer of unverifiable prose on top of it."
time_horizon: short
measures:
  - { id: OC-001-M1, measure: "Shown claims that passed every citation check", target: 100, unit: "percent" }
  - { id: OC-001-M2, measure: "False positives in an evaluation run (a statement whose meaning is in no passage it rests on)", target: 0, unit: "statements" }
  - { id: OC-001-M3, measure: "Grounded share of the agent's proposed claims in an evaluation run", target: "rising release on release", unit: "percent" }
owned_by_platform: PL-001
requires_capabilities: [CAP-004, CAP-005, CAP-008, CAP-011]
realised_by_use_cases: [UC-001, UC-006, UC-007]
provenance:
  origin: ai-generated
  review_state: ai-raw
supported_by_use_cases: [UC-001, UC-006, UC-007]
---

# OC-001 Answers a reader can check

| Property | Value |
|---|---|
| Outcome ID | OC-001 |
| Measure | Share of shown statements that passed the citation and grounding checks |
| Owned by | PL-001 Knowledge Store |

## Definition

Every statement the store shows a person is a claim with a citation: a passage and a verbatim quote, or a table cell or a figure recomputed from its snapshot. Code checks each citation before the claim is shown, and a claim that fails is repaired once or removed. When nothing passes, the answer says the sources cannot answer and what was missing.

## Business rationale

Retrieval-augmented answering without this discipline produces fluent prose that a reader has to trust. An organisation's documents already carry the authority; the store's job is to point at them exactly, so a reader checks a sentence by clicking it. The measure is structural: M1 is 100 percent because nothing else is shown, and M2 and M3 are what evaluation runs report (CAP-011), so the outcome is held against the sets in `examples/evals`.

## Traceability

Requires CAP-004 fact extraction with provenance (the facts carry their passages), CAP-005 the graph as record (the citation can be resolved), CAP-008 grounded answering (the checks) and CAP-011 evaluation (the measure). Realised by UC-001 ask a question and UC-007 evaluate the answers.
