---
kind: consideration
id: CN-006
title: "CN-006 Decoupling the deployables along the bounded contexts"
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
consideration_status: open
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

Status: open. Affects BC-001, BC-002, BC-003, BC-004, BC-005, BC-006, ABB-024, ABB-019, SV-001, SV-003, SV-004.

The architecture is expressed first; the decoupling follows it rather than gates it. The seams are already visible: the lake layout and the pointers between sweep stages, and the index module between the tools and the portal. The third option is the smallest step that satisfies the rule for answering.

Under the [building block calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md) the pipeline is one container, ABB-024, and its stages are components: the contexts BC-002 and BC-003 have no container of their own until this consideration is resolved by the second or fourth option. The Chat API, ABB-019, carries the fallback loop and the index views for the same reason.
