---
kind: bounded-context
id: BC-007
title: "BC-007 Evaluation"
description: "Evaluation sets, runs and scores: knowing whether the answers are right without a model as judge."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
part_of: PL-001
contains: [ABB-021]
realises_capabilities: [CAP-011]
subdomain_kind: supporting
c4_levels: [container, component]
ubiquitous_language:
  - { term: "Set", definition: "A YAML file of questions for one collection" }
  - { term: "Question kind", definition: "lookup, list, multi-hop, aggregate, comparison, unanswerable" }
  - { term: "Must, must not, first", definition: "The facts a right answer states, the near miss it must not, two names whose order matters" }
  - { term: "Correct", definition: "Every must found, no must not, the order right; for an unanswerable question, an abstention" }
  - { term: "Grounded share", definition: "Claims shown over claims proposed" }
  - { term: "False negative, false positive", definition: "Abstained on an answerable question; answered an unanswerable one" }
relationships:
  - { with: BC-005, pattern: customer-supplier, role: downstream }
  - { with: BC-004, pattern: customer-supplier, role: downstream }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# BC-007 Evaluation

| Property | Value |
|---|---|
| Context ID | BC-007 |
| Platform | PL-001 Knowledge Store |
| Owner team | Patternode (Dermot O'Brien) |
| Subdomain | supporting |
| Realises | CAP-011 |
| Contains | ABB-021 |

Evaluation sets, runs and scores: knowing whether the answers are right without a model as judge.

## Ubiquitous language

| Term | Meaning in this context |
|---|---|
| Set | A YAML file of questions for one collection |
| Question kind | lookup, list, multi-hop, aggregate, comparison, unanswerable |
| Must, must not, first | The facts a right answer states, the near miss it must not, two names whose order matters |
| Correct | Every must found, no must not, the order right; for an unanswerable question, an abstention |
| Grounded share | Claims shown over claims proposed |
| False negative, false positive | Abstained on an answerable question; answered an unanswerable one |

## Where the model lives today

- `evals/score.py, run.py (the set format, the runner against a lake or the API, deterministic scoring, the report)`
- `examples/evals/ (the space-missions and Sherlock Holmes sets)`

Runs are started by hand and cost a model call per question; the two shipped sets are the evidence the capabilities cite.

## Relationships with other contexts

| With | Pattern | Role | Why |
|---|---|---|---|
| BC-005 | customer-supplier | downstream | Asks the agent in process or through the API |
| BC-004 | customer-supplier | downstream | In-process runs use the local tools |

## Building blocks

ABB-021 Evaluation runner, a page under [../abbs](../../abbs/README.md).
