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
  - { term: "Correct", definition: "Every must and figure found, no must not, the order right; for an unanswerable question, a decline" }
  - { term: "Grounded share", definition: "Claims shown over claims proposed" }
  - { term: "False answer", definition: "An unanswerable question answered with a stated fact; a reply that declines, even with a citation, is not one" }
  - { term: "False abstention", definition: "An answerable question declined" }
  - { term: "Unsupported claim", definition: "A claim, on any question, that the claim verifier finds its cited source does not support" }
  - { term: "Baseline gate", definition: "A run compared with the kept baseline: a regression, a fall in accuracy, or a rise in false answers or unsupported claims fails it" }
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
| Correct | Every must and figure found, no must not, the order right; for an unanswerable question, a decline |
| Grounded share | Claims shown over claims proposed |
| False answer | An unanswerable question answered with a stated fact; a reply that declines, even with a citation, is not one |
| False abstention | An answerable question declined |
| Unsupported claim | A claim, on any question, that the claim verifier finds its cited source does not support |
| Baseline gate | A run compared with the kept baseline: a regression, a fall in accuracy, or a rise in false answers or unsupported claims fails it |

## Where the model lives today

- `evaluation/domain/` (sets: the format; score: the measures; numeric: figures at their stated rounding; compare: the baseline gate)
- `evaluation/ports.py` (Answerer, TruthSource, ClaimVerifier, Grader, RunStore, Runner)
- `evaluation/slices/` (run_set, gate) and `evaluation/adapters/` (answerers, set_files, run_store, report, verifiers, deepeval_cases, deepeval_grader, deepeval_runner)
- `apps/evaluate.py` (the command) and `examples/evals/` (the space-missions and Sherlock Holmes sets)

Runs are started by hand and cost a model call per question; the two shipped sets are the evidence the capabilities cite. The measures, the claim verifier and the gate are patternode-architecture ADR-048; the score itself stays free of model judges. DeepEval is the evaluation framework (ADR-013): an optional runner that records each run as a DeepEval test run, and a model grader (G-Eval correctness and faithfulness) reported beside the score.

## Relationships with other contexts

| With | Pattern | Role | Why |
|---|---|---|---|
| BC-005 | customer-supplier | downstream | Asks the agent in process or through the API |
| BC-004 | customer-supplier | downstream | In-process runs use the local tools |

## Building blocks

ABB-021 Evaluation runner, a page under [../abbs](../../abbs/README.md).
