---
kind: decision-record
id: ADR-011
title: "ADR-011 The code is cut by bounded context, and a deployable splits off only on a trigger"
version: 1.0.0
status: active
created: 2026-10-20
last_modified: 2026-10-20
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
y_statement: "In the context of eight bounded contexts read from code organised by capability, with two import cycles and deployables that compose several contexts, facing the choice between keeping the code as it was, splitting a deployable per context, and cutting the code by context while deployables stay composed, we decided for one package per context, each with a pure domain, feature slices, ports only where an adapter varies, adapters and one contract, composition roots in apps/, and checks in the test run, and against a deployable per context, to achieve boundaries that hold and can be extracted as a change to infrastructure, accepting that a deployable still runs several contexts until a trigger (another runtime, two versions at once, failure isolation, a different scaling or cost profile) applies."
decision_drivers: ["Boundaries that hold under change, including changes made by agents", "Extraction as an infrastructure change, not a rewrite", "No new images, roles or pipelines without a reason"]
considered_options:
  - "Keep the code organised by capability"
  - "A deployable per context"
  - "Code cut by context, deployables split on a trigger"
decision_outcome: "Code cut by context, deployables split on a trigger"
consequences:
  positive:
    - "import-linter and tests/test_architecture.py fail a pull request that crosses a boundary"
    - "Both import cycles are cut; the read tools are one slice every surface calls"
    - "Neptune, passage search and model access sit behind ports"
  negative:
    - "Module paths changed: Lambda handlers, the agent image's command and the evaluation command moved"
    - "The model client's port still speaks Bedrock's Converse shape"
change_type: introduce
affects_artefacts: [BC-001, BC-002, BC-003, BC-004, BC-005, BC-006, BC-007, BC-008, SV-001, SV-002, SV-003, SV-004, SV-005, SV-006, SV-009]
resolves: [CN-006]
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ADR-011 The code is cut by bounded context, and a deployable splits off only on a trigger

Status: active. This is Knowledge Store's application of patternode-architecture ADR-046 (contexts, slices and ports), made on 20 October 2026.

## Context

The eight contexts were a reading of code organised by capability. Eight pairs of packages imported each other, the tools Lambda imported the portal's chat and index modules, Neptune and passage search bypassed the ports, model calls were written in Bedrock's message format, and configuration was read in more than fifteen modules. CN-006 asked whether the deployables should follow the contexts.

## Decision

In the context of eight bounded contexts read from code organised by capability, with two import cycles and deployables that compose several contexts, facing the choice between keeping the code as it was, splitting a deployable per context, and cutting the code by context while deployables stay composed, we decided for one package per context, each with a pure domain, feature slices, ports only where an adapter varies, adapters and one contract, composition roots in apps/, and checks in the test run, and against a deployable per context, to achieve boundaries that hold and can be extracted as a change to infrastructure, accepting that a deployable still runs several contexts until a trigger (another runtime, two versions at once, failure isolation, a different scaling or cost profile) applies.

## Options considered

- Keep the code organised by capability
- A deployable per context
- Code cut by context, deployables split on a trigger

## Consequences

Positive: import-linter and tests/test_architecture.py fail a pull request that crosses a boundary. Both import cycles are cut; the read tools are one slice every surface calls. Neptune, passage search and model access sit behind ports.

Negative: Module paths changed: Lambda handlers, the agent image's command and the evaluation command moved. The model client's port still speaks Bedrock's Converse shape.

## Affects

BC-001 to BC-008, SV-001 to SV-006 and SV-009. Resolves CN-006.
