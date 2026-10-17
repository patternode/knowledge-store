---
kind: abb
id: ABB-024
title: "ABB-024 Ingestion and extraction pipeline"
short_name: "PIPE"
description: "One container that takes a collection from uploaded bytes to published, checkable facts: it acquires, refines, discovers and reviews an ontology, extracts with provenance, binds tables, projects and loads, in one idempotent sweep under a lock. It composes four bounded contexts today (CN-006)."
version: 0.2.0
status: draft
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Processing"
part_of: BC-001
realises_capabilities: [CAP-002, CAP-003, CAP-004, CAP-005, CAP-006, CAP-007]
realised_by: [SBB-002]
requires:
  - { abb: ABB-002, cardinality: "1", rationale: "Reads and writes every layer; the lock and the status live there" }
  - { abb: ABB-011, cardinality: "0..1", rationale: "Loads the named graphs when a graph is configured" }
  - { abb: ABB-013, cardinality: "0..1", rationale: "Syncs passages when the index is configured" }
domains: [application, data]
interfaces:
  - { id: "I1", direction: "in", type: "event", description: "An upload event, a schedule, or a command: one sweep (CT-005)" }
  - { id: "I2", direction: "out", type: "query", description: "Bronze, silver, gold, the candidate register, drafts and a published provided version, written to the lake" }
  - { id: "I3", direction: "out", type: "request", description: "Named graphs loaded into the knowledge graph; passages synced into the passage index; optional loads into the projection backends" }
  - { id: "I4", direction: "out", type: "request", description: "Discovery, review and extraction calls to the model, each priced into the ledger" }
  - { id: "I5", direction: "out", type: "query", description: "portal/status.json per collection: stage, active version, drafts, counts, last run" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/pipeline/run.py (the sweep)", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-024 Ingestion and extraction pipeline

| Property | Value |
|---|---|
| ABB ID | ABB-024 |
| ABB Name | Ingestion and extraction pipeline |
| Short Name | PIPE |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0, recalibrated to container grain |
| Category | Processing |
| Bounded context | BC-001 |
| Realises | CAP-002, CAP-003, CAP-004, CAP-005, CAP-006, CAP-007 |
| Realised by | SBB-002 |
| Grain | One C4 container: passes the container test of the [calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md) |

One container that takes a collection from uploaded bytes to published, checkable facts: it acquires, refines, discovers and reviews an ontology, extracts with provenance, binds tables, projects and loads, in one idempotent sweep under a lock. It composes four bounded contexts today (CN-006).

This block absorbed ABB-001 Source adapters, ABB-003 Document refinement, ABB-004 Sweep orchestration, ABB-005 Ontology discovery and review, ABB-006 Ontology versioning and renditions, ABB-007 Candidate register and revision proposal, ABB-008 Table mapping definition, ABB-009 Ontology-guided extraction, ABB-010 Table binding, ABB-011 Graph record and projection, ABB-013 Passage search by meaning, ABB-022 Model access and ledger under the [calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md): each ran inside this container's process and none passed the container test, so each is a component row below and its identifier is retired.

## 1  Purpose

The store stays current without an operator because every stage runs again safely and one sweep runs at a time. The pipeline is the container; its stages are components, each the model of one bounded context (ingestion, ontology, extraction, knowledge graph) that runs inside this one process until the deployables are split along the contexts.

## 2  Building block

### 2.1  Component Diagram

The components below are the boxes of this container's component diagram, which is not yet drawn. The outside view of this block is its box in [PAT-001](../../patterns/PAT-001-ontology-driven-graphrag/index.md) and the row of its SBB in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Components

- **Stages in order.** ingest, provided ontology, refine, discover (when no version), extract, bind, candidates, project, load graph, load documents, load SPARQL, sync passages, status; repeated until a round changes nothing
- **Lock and rounds.** One sweep at a time by a conditional write in the lake; a stale lock is taken over; each stage skips what is done by markers, pointers and hashes
- **Adapter protocol.** type, items(), fetch(item); a value object per item (folded from ABB-001 Source adapters)
- **Built-in adapters.** S3 landing (the default, per collection), local directory, HTTPS URLs with public-address and redirect checks (folded from ABB-001 Source adapters)
- **Registry.** Built-ins first, then entry points, chosen by the source's type (folded from ABB-001 Source adapters)
- **Parsers.** By extension then content type: text, markdown, HTML (table rows kept on one line), JSON (flattened), PDF; size caps (folded from ABB-003 Document refinement)
- **Chunking.** About 1,800 characters, at most 3,000, with an id from the document id, the sequence and the chunk hash; a chunker version string (folded from ABB-003 Document refinement)
- **Skip rules.** Unsupported, failed, empty, or mapped (a table the mapping names is not prose) (folded from ABB-003 Document refinement)
- **Stages in order.** ingest, provided ontology, refine, discover (when no version), extract, bind, candidates, project, load graph, load documents, load SPARQL, sync passages, status (folded from ABB-004 Sweep orchestration)
- **Rounds.** Up to five, until nothing new is stored or discovered (folded from ABB-004 Sweep orchestration)
- **Lock.** Conditional write with owner and TTL (folded from ABB-004 Sweep orchestration)
- **Status.** Written at each stage and on failure (folded from ABB-004 Sweep orchestration)
- **Sampling.** Round robin across sources, seeded, up to twenty documents twice, eight passages each (folded from ABB-005 Ontology discovery and review)
- **Proposal.** Per document: classes, relations, attributes with definitions and verbatim examples (folded from ABB-005 Ontology discovery and review)
- **Aggregation.** By normalised name, with document counts, stability and Jaccard overlap (folded from ABB-005 Ontology discovery and review)
- **Consolidation.** One call to about fifteen classes with hierarchy, domains, ranges, datatypes, and what was rejected (folded from ABB-005 Ontology discovery and review)
- **Review.** Edits only: parent, merge, drop, domain, range, datatype; cycles and unknown terms skipped (folded from ABB-005 Ontology discovery and review)
- **Writer.** Turtle with evidence comments and generated SHACL (folded from ABB-005 Ontology discovery and review)
- **Diff and classification.** descriptive, additive, semantic, removal; the mapping change folded in; the bump checked (folded from ABB-006 Ontology versioning and renditions)
- **Publish.** Refuses an existing version or a non-semver one; writes master, shapes, manifest, renditions (folded from ABB-006 Ontology versioning and renditions)
- **Chain.** An additive version's gold holds its delta; the graph is the union back to the last full version (folded from ABB-006 Ontology versioning and renditions)
- **Activate.** One pointer per collection (folded from ABB-006 Ontology versioning and renditions)
- **Renditions.** agent markdown and JSON, Neo4j schema and mapping, AGE schema, extraction tool schema, JSON-LD context, structured mapping JSON, R2RML (folded from ABB-006 Ontology versioning and renditions)
- **Provided ontology.** A master from configuration, published when newer, refused when changed without a bump (folded from ABB-006 Ontology versioning and renditions)
- **Register.** By kind and normalised term: documents, evidence, nearest, covered_by from synonyms, asked and questions from requests (folded from ABB-007 Candidate register and revision proposal)
- **Proposal.** Terms with two or more documents or a request, not covered; consolidated with the prior version; a warning when the result would change an existing term (folded from ABB-007 Candidate register and revision proposal)
- **Mapping model.** tables, logical table, location, class, key, scope, columns as attribute or relation with datatype, range, match (folded from ABB-008 Table mapping definition)
- **Checks.** Class exists, attribute domain fits, datatype agrees, range is a class, match is present, names unique; metric SELECT is read-only and names a logical table (folded from ABB-008 Table mapping definition)
- **Renditions.** JSON for the sweep and tools; R2RML for Ontop later (folded from ABB-008 Table mapping definition)
- **Tool schema.** record_knowledge generated from the version: entities, attributes, relations, candidates (folded from ABB-009 Ontology-guided extraction)
- **Extractor loop.** Converse with throttle retry; up to two repairs; salvage of what passed (folded from ABB-009 Ontology-guided extraction)
- **Checks.** Shape, ontology, grounding (names and values in cited passages), SHACL with inference (folded from ABB-009 Ontology-guided extraction)
- **RDF builder.** Content-derived IRIs; reified assertions with extractedFrom, extractedBy; N-Quads (folded from ABB-009 Ontology-guided extraction)
- **Delta.** Selection by candidate, lexical match or retype; new terms only; ks:delta (folded from ABB-009 Ontology-guided extraction)
- **File selection.** Exact path, suffix, then name; ties refused; size and row caps (folded from ABB-010 Table binding)
- **Row to entity.** Class plus key columns as the IRI; relations joined within the snapshot; a miss recorded (folded from ABB-010 Table binding)
- **Cells.** Column, canonical value, raw text, snapshot, row key, scope (folded from ABB-010 Table binding)
- **Binding record.** Per logical table: source, snapshot, mapping hash, scope, counts (folded from ABB-010 Table binding)
- **Re-bind rule.** When the hash, the mapping hash or the scope changed (folded from ABB-010 Table binding)
- **Projection.** Summary, ontology with counts, entities, passages, documents as JSON per version (folded from ABB-011 Graph record and projection)
- **SPARQL load.** DROP and INSERT per named graph, skipping unchanged hashes, dropping graphs off the chain, counting triples (folded from ABB-011 Graph record and projection)
- **Graph backend load.** Nodes with class labels and ancestors, edges with passages and scope; counts checked before the pointer moves; the previous build kept (folded from ABB-011 Graph record and projection)
- **Document load.** Entities, passages, documents into MongoDB with multikey indexes (folded from ABB-011 Graph record and projection)
- **Pointers.** graph.json, documents.json, sparql.json, kb.json (folded from ABB-011 Graph record and projection)
- **Sync.** Per-passage hash of text, scope and title; deletions; one ingestion job per change (folded from ABB-013 Passage search by meaning)
- **Retrieve.** Filtered, then re-checked against metadata (folded from ABB-013 Passage search by meaning)
- **Keyword fallback.** tf-idf over the index when the Knowledge Base is off (folded from ABB-013 Passage search by meaning)
- **Read.** From the projection, then silver (folded from ABB-013 Passage search by meaning)
- **Provider seam.** bedrock or anthropic; model name mapping; parameters a model rejects dropped per family; throttling mapped to one exception (folded from ABB-022 Model access and ledger)
- **Ledger client.** Wraps any Converse client; buffers; flushes to usage/ledger/dt=<day>/ (folded from ABB-022 Model access and ledger)
- **Prices.** A table of list prices with batch and regional factors (folded from ABB-022 Model access and ledger)
- **Strands model.** The same choice for the agent framework (folded from ABB-022 Model access and ledger)

### 2.3  Attributes

- **Idempotence.** Same bytes, same passages, same ids, across sweeps and machines; each stage skips what is done
- **Safety.** Only one sweep at a time; document content is untrusted and never executed
- **Cost bound.** Discovery samples a fixed number of documents; extraction runs once per document per version
- **Convergence.** The sweep repeats until a round changes nothing

### 2.4  Semantic

Inside: every stage from bytes to loaded projections, the lock, the rounds and the status. Outside: the stores it writes (ABB-002, ABB-011, ABB-013), the model it calls, the command line that publishes and activates a version by hand (ABB-028), and the tools that read what it wrote.

### 2.5  Identity & Access Management

The task role: the lake, Neptune write, the Knowledge Base ingestion job, the model with grants scoped to the configured ids, the Anthropic key from the secret store when that provider is chosen. Started by the EventBridge Pipes and Scheduler roles, which may only run the task.

### 2.6  Observability

The task log group; the status per collection; per-stage counts; a dead-letter queue for uploads that could not start a task; every model call in the ledger.

### 2.7  Governance & Policy Enforcement

Schedule, workers and sources are deployment inputs. The sweep is the only writer of gold, of the candidate register and of the knowledge graph. A published version is immutable and the bump decides the cost (ADR-005). Formats and tool schemas are code.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | event | An upload event, a schedule, or a command: one sweep (CT-005) |
| I2 | out | query | Bronze, silver, gold, the candidate register, drafts and a published provided version, written to the lake |
| I3 | out | request | Named graphs loaded into the knowledge graph; passages synced into the passage index; optional loads into the projection backends |
| I4 | out | request | Discovery, review and extraction calls to the model, each priced into the ledger |
| I5 | out | query | portal/status.json per collection: stage, active version, drafts, counts, last run |

### 3.4  Capability dependencies (requires)

- ABB-002 (1): Reads and writes every layer; the lock and the status live there
- ABB-011 (0..1): Loads the named graphs when a graph is configured
- ABB-013 (0..1): Syncs passages when the index is configured

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/pipeline/run.py (the sweep), ingest.py, refine.py, extract.py, project.py, load.py; adapters/; refine/; ontology/discover.py, review.py, writer.py, versions.py, renditions.py, provided.py, candidates.py; extract/; structured/mapping.py, bind.py; graph/; llm.py, ledger.py; infra/modules/pipeline` |
| Capabilities | CAP-002, CAP-003, CAP-004, CAP-005, CAP-006, CAP-007 |
| Context | BC-001 |

## 5  Solution Building Block guidance

Realised as the pipeline image run as an ECS Fargate task started by uploads and a schedule (SBB-002). The same code runs in process under the command line on an operator's machine (ABB-028, SBB-013). Splitting it along the contexts is CN-006.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain: absorbed ABB-001, ABB-003, ABB-004, ABB-005, ABB-006, ABB-007, ABB-008, ABB-009, ABB-010, ABB-011, ABB-013, ABB-022; new in the calibration |
