---
kind: consideration
id: CN-006
title: "CN-006 Decoupling the deployables along the bounded contexts"
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-20
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
consideration_status: resolved
resolved_by: ADR-011
question: "The pipeline image composes four contexts and the portal Lambda composes three. Should the deployables follow the contexts, and in what order?"
options:
  - { name: "Keep the as-built composition", summary: "One sweep task, one portal Lambda; the contexts are a reading of the code" }
  - { name: "Split the sweep by stage", summary: "A task per context (ingestion, ontology, extraction, graph loading), the lake layout as the contract between them" }
  - { name: "Move the index out of the portal", summary: "The tools own the index and the SPARQL index; the portal keeps routes, state and identity; the fallback loop retires" }
  - { name: "Split everything", summary: "A deployable per context, including evaluation as a scheduled job" }
criteria:
  - "A service serves one context (the continuum's rule)"
  - "No change to the lake layout or the contracts"
  - "Cost in images and roles"
  - "The two import cycles cut"
affects: [BC-001, BC-002, BC-003, BC-004, BC-005, BC-006, ABB-024, ABB-019, SV-001, SV-003, SV-004]
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# CN-006 Decoupling the deployables along the bounded contexts

The pipeline image composes four contexts and the portal Lambda composes three. Should the deployables follow the contexts, and in what order?

| Option | Summary |
|---|---|
| Keep the as-built composition | One sweep task, one portal Lambda; the contexts are a reading of the code |
| Split the sweep by stage | A task per context (ingestion, ontology, extraction, graph loading), the lake layout as the contract between them |
| Move the index out of the portal | The tools own the index and the SPARQL index; the portal keeps routes, state and identity; the fallback loop retires |
| Split everything | A deployable per context, including evaluation as a scheduled job |

Criteria: A service serves one context (the continuum's rule); No change to the lake layout or the contracts; Cost in images and roles; The two import cycles cut.

Status: resolved on 2026-10-20 (see Resolution). Affects BC-001, BC-002, BC-003, BC-004, BC-005, BC-006, ABB-024, ABB-019, SV-001, SV-003, SV-004.

The architecture is expressed first; the decoupling follows it rather than gates it. The seams are already visible: the lake layout and the pointers between sweep stages, and the index module between the tools and the portal. The third option is the smallest step that satisfies the rule for answering.

Under the [building block calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md) the pipeline is one container, ABB-024, and its stages are components: the contexts BC-002 and BC-003 have no container of their own until this consideration is resolved by the second or fourth option. The Chat API, ABB-019, carries the fallback loop and the index views for the same reason.

## Resolution

Resolved on 20 October 2026 by ADR-011, Knowledge Store's application of patternode-architecture ADR-046 (contexts, slices and ports). The code now follows the contexts: one package per context, each with one contract, and import-linter checks the boundaries on every test run. Both import cycles are cut. The read tools are a Knowledge Graph slice, and the portal API reads the index through Knowledge Graph's contract, which is the third option done in the code.

The deployables do not yet follow the contexts one for one, and need not. Under ADR-046 a context is deployed on its own only on an ADR-044 trigger: another runtime, two hosts at different versions, failure isolation, or a different scaling or cost profile. Each deployable's composition root is in `apps/`: the sweep, the portal API, the agent, the command line and the evaluation runner. Extraction's model-heavy batch work is the first context that meets a trigger (its cost and scaling differ from ingestion's). Splitting it into a task of its own, with the lake layout as the contract between stages (the second option), is a Terraform change for the master session, and Dermot applies it. Splitting everything (the fourth option) is not taken.

