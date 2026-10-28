---
kind: decision-record
id: ADR-013
title: "ADR-013 DeepEval is the evaluation framework, beside the deterministic score"
version: 1.0.0
status: active
created: 2026-10-22
last_modified: 2026-10-22
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
y_statement: "In the context of an evaluator whose score is deterministic and whose only framework was Inspect AI as an optional runner with no grader, facing the choice between keeping Inspect AI, adopting DeepEval, and writing a grader of our own, we decided for DeepEval as the runner and the model grader, with G-Eval correctness and faithfulness judged through the platform's model client and reported beside the score, and against a model judge in the score or a hand-written grader, to achieve a judgement of meaning that a reference architecture's users already know, without moving the score off its deterministic measures, accepting a pinned, fast-moving dependency and a judge whose verdicts vary between models."
decision_drivers: ["The score stays free of model judges (UC-007, ADR-012)", "A grader for meaning the lexical measures miss", "A framework the reference architecture's users already know", "Nothing leaves the account unasked"]
considered_options:
  - "Keep Inspect AI as the optional runner, with no grader"
  - "DeepEval as the runner and the grader, beside the score"
  - "A grader of our own on the platform's model client"
decision_outcome: "DeepEval as the runner and the grader, beside the score"
consequences:
  positive:
    - "Correctness and faithfulness are judged on every graded question, and shown beside the score"
    - "A run is a DeepEval test run, readable with DeepEval's tools"
    - "The judge goes through Bedrock or the Anthropic API and the call ledger, never OpenAI"
  negative:
    - "DeepEval is pinned; its metrics' prompts change between releases, so a bump is a recalibration"
    - "A grade costs about five judge calls a question"
    - "Inspect AI's runner and its log viewer are gone"
change_type: replace
affects_artefacts: [BC-007, SV-009, ABB-021, SBB-019]
resolves: []
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ADR-013 DeepEval is the evaluation framework, beside the deterministic score

Status: active, made on 22 October 2026. It replaces the Inspect AI runner that [ADR-012](ADR-012-evaluation-counts-false-answers-and-unsupported-claims-and-gates-releases.md) named as optional, and keeps ADR-012's measures and gate as they are.

## Context

ADR-012 kept the score deterministic: facts stated, near misses avoided, declines, claims checked against what they cite, and a baseline gate. It named Inspect AI as an optional runner and left a model grader to applications. The Grader port existed, but nothing implemented it, so an answer that states the expected fact in other words, or one whose claims are true but unsupported by its passages in meaning, was judged only by word matching and the claim verifier.

## Decision

In the context of an evaluator whose score is deterministic and whose only framework was Inspect AI as an optional runner with no grader, facing the choice between keeping Inspect AI, adopting DeepEval, and writing a grader of our own, we decided for DeepEval as the runner and the model grader, with G-Eval correctness and faithfulness judged through the platform's model client and reported beside the score, and against a model judge in the score or a hand-written grader, to achieve a judgement of meaning that a reference architecture's users already know, without moving the score off its deterministic measures, accepting a pinned, fast-moving dependency and a judge whose verdicts vary between models.

How it is built:

- `DeepEvalGrader` (the Grader port) runs G-Eval correctness against the set's expected answer and answer facts, and DeepEval's faithfulness metric against the passages the answer cites. Each runs only when the question gives it something to judge. Its verdict (pass, partial, fail or skipped) and each metric's score and reason go in the row's `grade` and the report's Grader section; `correct` and `score` never read them.
- `DeepEvalRunner` (the Runner port) asks and scores every question as the plain loop does, then records the rows as a DeepEval test run, with the score and each grader metric as metrics that read the rows back. It calls no model.
- The judge is a DeepEval model over the platform's Converse client, so its calls go to Bedrock or the Anthropic API and into the call ledger. DeepEval's telemetry is off, its `.env` loading is off, and a run goes to Confident AI only when asked (`--upload-to-confident`); with a Confident AI key set and no such flag, the runner refuses to start.
- DeepEval is in the `evals` extra, pinned to one release.

## Options considered

- Keep Inspect AI as the optional runner, with no grader
- DeepEval as the runner and the grader, beside the score
- A grader of our own on the platform's model client

## Consequences

Positive: Correctness and faithfulness are judged on every graded question, and shown beside the score. A run is a DeepEval test run, readable with DeepEval's tools. The judge goes through Bedrock or the Anthropic API and the call ledger, never OpenAI.

Negative: DeepEval is pinned; its metrics' prompts change between releases, so a bump is a recalibration. A grade costs about five judge calls a question. Inspect AI's runner and its log viewer are gone.

## Affects

BC-007, SV-009, ABB-021, SBB-019.
