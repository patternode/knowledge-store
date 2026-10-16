---
kind: capability
id: CAP-003
title: "CAP-003 Ontology lifecycle management"
description: "Bringing or discovering an ontology for a collection, reviewing and curating it, publishing immutable classified versions with their renditions, and growing it from what extraction could not place."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
level: L2
parent: CAP-001
components:
  organisation: "Curators own each collection's ontology; the product owner owns the core vocabulary"
  people: ["Curators", "Ontology engineers bringing a standard's ontology"]
  processes:
    - "Bring an ontology (ontology_dir) and bump owl:versionInfo to change it"
    - "Discover from a sample, review, write a draft"
    - "Pull, edit in git, diff, publish, activate"
    - "Classify a change and refuse an understated bump"
    - "Render every rendition at publish"
    - "Register candidates and propose the next minor version"
  technology: "OWL Turtle masters, generated SHACL, a manifest per version with checksums, renditions for the agent, the graph stores, extraction and JSON-LD"
maturity:
  current: 4
  target: 5
  assessment_date: 2026-10-16
  assessor: "Patternode (Dermot O'Brien), reversed from the implementation"
subdomain_kind: core
provided_by_platform: PL-001
realised_by_abbs: [ABB-005, ABB-006, ABB-007, ABB-008]
gaps:
  - "Only Turtle is a master format (the MASTERS registry holds one reader)"
  - "No user interface for curation: pull and publish are CLI steps"
  - "Auto mode publishes a first draft without review by a person"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# CAP-003 Ontology lifecycle management

| Property | Value |
|---|---|
| Capability ID | CAP-003 |
| Level | L2 |
| Parent | CAP-001 |
| Status | Draft, reversed from the implementation at 0.3.0 |
| Subdomain | core |
| Maturity | 4, target 5 |
| Realised by | ABB-005, ABB-006, ABB-007, ABB-008 |

Bringing or discovering an ontology for a collection, reviewing and curating it, publishing immutable classified versions with their renditions, and growing it from what extraction could not place.

## 1  Purpose

The ontology is what makes the graph the organisation's rather than the model's. This capability keeps a person in charge of it: a draft is proposed, a person publishes, a version number says what changed and what it costs, and consumers read renditions rather than the master.

## 2  Capability definition

| Dimension | For Knowledge Store |
|---|---|
| Organisation | Curators own each collection's ontology; the product owner owns the core vocabulary |
| People | Curators, Ontology engineers bringing a standard's ontology |
| Processes | Bring an ontology (ontology_dir) and bump owl:versionInfo to change it; Discover from a sample, review, write a draft; Pull, edit in git, diff, publish, activate; Classify a change and refuse an understated bump; Render every rendition at publish; Register candidates and propose the next minor version |
| Technology | OWL Turtle masters, generated SHACL, a manifest per version with checksums, renditions for the agent, the graph stores, extraction and JSON-LD |

## 3  Sub-capabilities

| Sub-capability | What it covers | Status |
|---|---|---|
| Bring your own ontology | A provided master published and activated by configuration | In place |
| Discovery and review | A first draft from a sample, with reviewed edits | In place |
| Versioning and classification | Immutable versions, bump checked against the diff | In place |
| Renditions | Consumer forms rendered from the master at publish | In place |
| Growth | Candidates and requests into a proposed minor version | In place |
| Curation interface | A place other than git and the CLI to curate | Not started |

## 4  What the implementation does today

Discovery follows extract, define, canonicalise with a review pass whose edits are applied in code. Publish diffs against the active version, classifies the change (descriptive, additive, semantic, removal) together with the mapping change, and refuses a bump smaller than required. Versions chain back to the last full version. Eleven renditions are written per version. Candidates from extraction and requests from the workbench feed a proposed next version.

## 5  Maturity

Current maturity is 4 on the 0 to 5 scale, read from the implementation: the capability is defined, built and in service in the Patternode lab and in any deployment of the module. Target 5.

## 6  Gaps

- Only Turtle is a master format (the MASTERS registry holds one reader)
- No user interface for curation: pull and publish are CLI steps
- Auto mode publishes a first draft without review by a person
