---
kind: abb
id: ABB-028
title: "ABB-028 Command line"
short_name: "CLI"
description: "The command an operator or curator runs: the whole pipeline in one process over a folder or the bucket, the ontology release commands that publish, activate and propose versions under the release controls, the ledger report, and a local portal server."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Platform services"
part_of: BC-008
realises_capabilities: [CAP-002, CAP-003, CAP-004, CAP-005, CAP-007, CAP-008, CAP-010, CAP-013]
realised_by: [SBB-013]
requires:
  - { abb: ABB-002, cardinality: "1", rationale: "A folder lake or the bucket" }
domains: [application]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "knowledge-store run, ingest, refine, extract, project, discover, ontology (versions, activate, publish, candidates), ledger, serve (CT-014)" }
  - { id: "I2", direction: "out", type: "query", description: "A published, activated or proposed ontology version in the lake; a local sweep; a local portal" }
  - { id: "I3", direction: "out", type: "request", description: "Model calls as the operator, priced into the ledger" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "src/knowledge_store/cli.py", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-028 Command line

| Property | Value |
|---|---|
| ABB ID | ABB-028 |
| ABB Name | Command line |
| Short Name | CLI |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0, recalibrated to container grain |
| Category | Platform services |
| Bounded context | BC-008 |
| Realises | CAP-002, CAP-003, CAP-004, CAP-005, CAP-007, CAP-008, CAP-010, CAP-013 |
| Realised by | SBB-013 |
| Grain | One C4 container: passes the container test of the [calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md) |

The command an operator or curator runs: the whole pipeline in one process over a folder or the bucket, the ontology release commands that publish, activate and propose versions under the release controls, the ledger report, and a local portal server.

## 1  Purpose

A person needs a way to run the store on one machine and to act on the ontology deliberately. A command-line tool a person runs is a container by the standard's verdict: its own process and its own release. The release controls live here because a person, not the sweep, decides what the next version holds (ADR-005).

## 2  Building block

### 2.1  Component Diagram

The components below are the boxes of this container's component diagram, which is not yet drawn. The outside view of this block is its box in [AP-001](../../patterns/AP-001-ontology-driven-graphrag/index.md) and the row of its SBB in [RA-001](../../patterns/RA-001-knowledge-store-on-aws/index.md).

### 2.2  Components

- **Pipeline in process.** The same stages as the pipeline container, over a folder lake, with in-process tools and agent
- **Ontology release.** pull, diff, publish (classified by the diff), activate, candidates --propose; the controls on a version
- **Ledger report.** Cost per job, run and day from the ledger
- **Local portal.** The chat page and API served from the machine for development and evaluation

### 2.3  Attributes

- **Self-sufficiency.** Python 3.12 and credentials for one model provider
- **Same code.** No path exists only locally

### 2.4  Semantic

Inside: the commands and the local profile. Outside: the lake it works on and the model it calls.

### 2.5  Identity & Access Management

The person's own credentials: the Anthropic key or AWS credentials for Bedrock and, when pointed at a deployment, the bucket.

### 2.6  Observability

The command's own output and the ledger.

### 2.7  Governance & Policy Enforcement

Publishing and activating a version are commands a person runs, logged in the version's manifest; the lab follows a pinned release of this repository.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | request | knowledge-store run, ingest, refine, extract, project, discover, ontology (versions, activate, publish, candidates), ledger, serve (CT-014) |
| I2 | out | query | A published, activated or proposed ontology version in the lake; a local sweep; a local portal |
| I3 | out | request | Model calls as the operator, priced into the ledger |

### 3.4  Capability dependencies (requires)

- ABB-002 (1): A folder lake or the bucket

## 4  Mapping

| Where | What |
|---|---|
| Code | `src/knowledge_store/cli.py; ontology/versions.py (publish, activate); ontology/candidates.py (propose); ledger.py (report); portal_api/local.py` |
| Capabilities | CAP-002, CAP-003, CAP-004, CAP-005, CAP-007, CAP-008, CAP-010, CAP-013 |
| Context | BC-008 |

## 5  Solution Building Block guidance

Realised by the Python package installed on an operator's machine, the local profile (SBB-013).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain; new in the calibration |
