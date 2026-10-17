---
kind: decision-record
id: ADR-006
title: "ADR-006 One Terraform module, images built inside the account"
version: 1.0.0
status: active
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
y_statement: "In the context of how a deployment is made, facing the choice between a hosted service, a set of scripts, and one Terraform module, we decided for one module with nine submodules, a two-stage apply, both images built by CodeBuild in the account from the deployed source with only the base image pulled by digest, and a CloudFormation launch stack running the same Terraform, and against a hosted service, to achieve self-containment and a visible bill, accepting the second apply and an administrator-equivalent deployer in the launch stack."
decision_drivers: ["Custody of documents", "Supply chain", "Adoption in an afternoon"]
considered_options:
  - "A hosted service"
  - "Scripts and a container registry"
  - "One Terraform module built in-account"
decision_outcome: "One Terraform module built in-account"
consequences:
  positive:
    - "Mocked Terraform tests; a template pinned to a tag"
    - "Nothing listens without a verified token"
  negative:
    - "Two applies"
    - "The launch stack's trust boundary must be restricted by the account"
change_type: introduce
affects_artefacts: [BC-008]
resolves: []
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ADR-006 One Terraform module, images built inside the account

Status: active, as implemented at 0.3.0. This record is reversed from the implementation and the design notes; the decision was made in the code and the notes before it was written here.

## Context

A reference architecture is adopted when it is one thing to apply and nothing arrives from outside.

## Decision

In the context of how a deployment is made, facing the choice between a hosted service, a set of scripts, and one Terraform module, we decided for one module with nine submodules, a two-stage apply, both images built by CodeBuild in the account from the deployed source with only the base image pulled by digest, and a CloudFormation launch stack running the same Terraform, and against a hosted service, to achieve self-containment and a visible bill, accepting the second apply and an administrator-equivalent deployer in the launch stack.

## Options considered

- A hosted service
- Scripts and a container registry
- One Terraform module built in-account

## Consequences

Positive: Mocked Terraform tests; a template pinned to a tag; Nothing listens without a verified token.

Negative: Two applies; The launch stack's trust boundary must be restricted by the account.

## Affects

BC-008, .
