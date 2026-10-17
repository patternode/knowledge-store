---
kind: abb
id: ABB-006
title: "ABB-006 Ontology versioning and renditions"
short_name: "VERS"
description: "Publishing a master as an immutable version with a manifest of checksums, classifying the change against the active version to decide the bump and the re-extraction, chaining versions, activating one, and rendering the consumer forms."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Ontology"
part_of: BC-002
realises_capabilities: [CAP-003, CAP-007]
realised_by: [SBB-014]
requires:
  - { abb: ABB-002, cardinality: "1", rationale: "Versions live in the lake" }
  - { abb: ABB-008, cardinality: "0..1", rationale: "A mapping, when present, is classified with the version" }
domains: [application, data]
interfaces:
  - { id: "I1", direction: "in", type: "query", description: "A master directory: ontology.ttl, optional shapes.ttl, mappings.yaml, metrics.osi.yaml" }
  - { id: "I2", direction: "out", type: "query", description: "ontology/versions/<v>/ with the master, shapes, manifest and renditions (CT-006); ontology/active.json" }
  - { id: "I3", direction: "out", type: "query", description: "The change kind and the required bump; refusal when understated" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/ontology/versions.py, renditions.py, provided.py, model.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-006 Ontology versioning and renditions

| Property | Value |
|---|---|
| ABB ID | ABB-006 |
| ABB Name | Ontology versioning and renditions |
| Short Name | VERS |
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Ontology |
| Bounded context | BC-002 |
| Realises | CAP-003, CAP-007 |
| Realised by | SBB-014 |

Publishing a master as an immutable version with a manifest of checksums, classifying the change against the active version to decide the bump and the re-extraction, chaining versions, activating one, and rendering the consumer forms.

## 1  Purpose

Consumers must never read the master, and a version must say what it costs. Rendering at publish and classifying the diff make both true, and the chain makes additive versions cheap.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Diff and classification.** descriptive, additive, semantic, removal; the mapping change folded in; the bump checked
- **Publish.** Refuses an existing version or a non-semver one; writes master, shapes, manifest, renditions
- **Chain.** An additive version's gold holds its delta; the graph is the union back to the last full version
- **Activate.** One pointer per collection
- **Renditions.** agent markdown and JSON, Neo4j schema and mapping, AGE schema, extraction tool schema, JSON-LD context, structured mapping JSON, R2RML
- **Provided ontology.** A master from configuration, published when newer, refused when changed without a bump

### 2.3  Attributes

- **Immutability.** A published version never changes; checksums prove it
- **Reproducibility.** Two publishes of the same master render the same files

### 2.4  Semantic

Inside: versions, their classification and renditions. Outside: what consumers do with a rendition.

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

### 3.4  Capability dependencies (requires)

- ABB-002 (1): Versions live in the lake
- ABB-008 (0..1): A mapping, when present, is classified with the version

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/ontology/versions.py, renditions.py, provided.py, model.py` |
| Capabilities | CAP-003, CAP-007 |
| Context | BC-002 |

## 5  Solution Building Block guidance

Realised in the pipeline image and the CLI.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
