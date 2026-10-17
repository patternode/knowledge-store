---
kind: abb
id: ABB-006
title: "ABB-006 Ontology publisher"
short_name: "PUBLISH"
description: "The command a curator runs on the ontology: diff and classification against the active version, publish as an immutable version with its renditions and manifest, activation, pulling drafts and proposing a revision from the candidate register, the table mapping definition and its checks, and the ledger report. The sweep publishes a provided ontology and auto-publishes a draft with the same library."
version: 0.2.0
status: draft
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Ontology"
part_of: BC-002
realises_capabilities: [CAP-003, CAP-007]
realised_by: [SBB-015]
requires:
  - { abb: ABB-002, cardinality: "1", rationale: "Versions, drafts and the active pointer live in the lake" }
domains: [application, data]
interfaces:
  - { id: "I1", direction: "in", type: "query", description: "A master directory: ontology.ttl, optional shapes.ttl, mappings.yaml, metrics.osi.yaml" }
  - { id: "I2", direction: "out", type: "query", description: "ontology/versions/<v>/ with the master, shapes, manifest and renditions (CT-006); ontology/active.json" }
  - { id: "I3", direction: "out", type: "query", description: "The change kind and the required bump; refusal when understated" }
  - { id: "I7", direction: "in", type: "request", description: "The master, shapes and mapping from the curator's checkout" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/ontology/versions.py, renditions.py, provided.py, model.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-006 Ontology publisher

| Property | Value |
|---|---|
| ABB ID | ABB-006 |
| ABB Name | Ontology publisher |
| Short Name | PUBLISH |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Ontology |
| Bounded context | BC-002 |
| Realises | CAP-003, CAP-007 |
| Realised by | SBB-015 |

The command a curator runs on the ontology: diff and classification against the active version, publish as an immutable version with its renditions and manifest, activation, pulling drafts and proposing a revision from the candidate register, the table mapping definition and its checks, and the ledger report. The sweep publishes a provided ontology and auto-publishes a draft with the same library.

## 1  Purpose

Consumers must never read the master, and a version must say what it costs. Rendering at publish and classifying the diff make both true, and the chain makes additive versions cheap.

## 2  Building block

### 2.1  Component Diagram

The components below are what runs inside this one container, listed per the building block calibration standard: none of them is a building block of its own. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Diff and classification.** descriptive, additive, semantic, removal; the mapping change folded in; the bump checked
- **Publish.** Refuses an existing version or a non-semver one; writes master, shapes, manifest, renditions
- **Chain.** An additive version's gold holds its delta; the graph is the union back to the last full version
- **Activate.** One pointer per collection; the activation starts a sweep
- **Renditions.** agent markdown and JSON, Neo4j schema and mapping, AGE schema, extraction tool schema, JSON-LD context, structured mapping JSON, R2RML
- **Provided ontology.** A master from configuration, published when newer, refused when changed without a bump
- **Table mapping definition.** tables, logical table, location, class, key, scope, columns as attribute or relation; checks that the class exists, the domain fits, the datatype agrees, the range is a class, names are unique and a metric is read-only; rendered as JSON for the sweep and the tools and as R2RML
- **Drafts and proposals.** pull, diff and candidates --propose: a revision drafted from the register with the current ontology held fixed, warning when a term would change
- **Ledger report.** Model spend per job and day from the lake's ledger

### 2.3  Attributes

- **Immutability.** A published version never changes; checksums prove it
- **Reproducibility.** Two publishes of the same master render the same files

### 2.4  Semantic

Inside: what a curator does to an ontology between editing the master and seeing facts extracted against it. Outside: discovering a draft and extracting (ABB-004), and the stores the renditions are loaded into.

### 2.5  Identity & Access Management

Publish runs as the curator (CLI) or the pipeline task (provided, auto); the manifest records who.

### 2.6  Observability

The manifest: by, at, note, kind, changes, checksums.

### 2.7  Governance & Policy Enforcement

The bump rule is the governance: a person cannot understate a change. The core vocabulary is versioned separately.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | artefact | A master directory: ontology.ttl, optional shapes.ttl, mappings.yaml, metrics.osi.yaml |
| I2 | out | artefact | ontology/versions/<v>/ with the master, shapes, manifest and renditions (CT-006); ontology/active.json |
| I3 | out | classification | The change kind and the required bump; refusal when understated |
| I7 | in | config | The master, shapes and mapping from the curator's checkout |

### 3.4  Capability dependencies (requires)

- ABB-002 (1): Versions, drafts and the active pointer live in the lake

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/cli.py; ontology/versions.py, renditions.py, provided.py, model.py; structured/mapping.py` |
| Capabilities | CAP-003, CAP-007 |
| Context | BC-002 |

## 5  Solution Building Block guidance

Realised as the knowledge-store command on an operator's machine (SBB-015). Inside the sweep the same library publishes a provided ontology and auto-publishes a draft, as a component of ABB-004.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.2.0 | 2026-10-17 | Recalibrated to container grain: the command line is the container; ABB-008 folded in; renamed from Ontology versioning and renditions |
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
