---
kind: decision-record
id: ADR-007
title: "ADR-007 A passage index on S3 Vectors beside the graph"
version: 1.0.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
y_statement: "In the context of questions that share no words with their answer, facing the choice between graph only, an OpenSearch vector index and a Bedrock Knowledge Base on S3 Vectors, we decided for the Knowledge Base on S3 Vectors with one vector per passage and chunking off, switchable off per deployment with a keyword fallback, and against OpenSearch, to achieve meaning search at cents a month whose hit is a passage id the facts cite, accepting a single embedding model per deployment."
decision_drivers: ["Cost at rest", "The passage as the shared unit"]
considered_options:
  - "Graph only"
  - "OpenSearch Serverless"
  - "Knowledge Base on S3 Vectors"
decision_outcome: "Knowledge Base on S3 Vectors"
consequences:
  positive:
    - "Cents at rest"
    - "Same id in both paths"
  negative:
    - "Model change rebuilds the index"
change_type: introduce
affects_artefacts: [BC-004, ABB-013, ABB-025]
resolves: [CN-004]
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ADR-007 A passage index on S3 Vectors beside the graph

Status: active, as implemented at 0.3.0. This record is reversed from the implementation and the design notes; the decision was made in the code and the notes before it was written here.

## Context

The graph is reached by names and terms; frontline questions describe situations.

## Decision

In the context of questions that share no words with their answer, facing the choice between graph only, an OpenSearch vector index and a Bedrock Knowledge Base on S3 Vectors, we decided for the Knowledge Base on S3 Vectors with one vector per passage and chunking off, switchable off per deployment with a keyword fallback, and against OpenSearch, to achieve meaning search at cents a month whose hit is a passage id the facts cite, accepting a single embedding model per deployment.

## Options considered

- Graph only
- OpenSearch Serverless
- Knowledge Base on S3 Vectors

## Consequences

Positive: Cents at rest; Same id in both paths.

Negative: Model change rebuilds the index.

## Affects

BC-004, ABB-013, ABB-025. Resolves CN-004.
