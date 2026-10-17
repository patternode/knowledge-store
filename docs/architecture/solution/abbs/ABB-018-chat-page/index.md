---
kind: abb
id: ABB-018
title: "ABB-018 Chat page"
short_name: "PAGE"
description: "The static site a reader uses: the question, the answer with its claims, sources and steps, the ontology page, and the workbench panel for curators, embedded by a host website or served on its own."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Portal"
part_of: BC-006
realises_capabilities: [CAP-009, CAP-012]
realised_by: [SBB-018]
requires:
  - { abb: ABB-019, cardinality: "1", rationale: "Everything it shows comes through the API" }
  - { abb: ABB-020, cardinality: "1", rationale: "Signs the reader in, or carries the host's grant" }
domains: [application]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "A reader in a browser, signed in by code flow with PKCE or carried by a host website's grant (CT-016)" }
  - { id: "I2", direction: "out", type: "request", description: "HTTPS /api calls with the access token or the site grant (CT-001)" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "chat/index.html", ref: "main" }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# ABB-018 Chat page

| Property | Value |
|---|---|
| ABB ID | ABB-018 |
| ABB Name | Chat page |
| Short Name | PAGE |
| Version | 0.2.0 |
| Status | draft, reversed from the implementation at 0.3.0, recalibrated to container grain |
| Category | Portal |
| Bounded context | BC-006 |
| Realises | CAP-009, CAP-012 |
| Realised by | SBB-018 |
| Grain | One C4 container: passes the container test of the [calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md) |

The static site a reader uses: the question, the answer with its claims, sources and steps, the ontology page, and the workbench panel for curators, embedded by a host website or served on its own.

## 1  Purpose

Grounding has to be visible to be trusted: the page shows every claim with its citation and every step with its cost. It is a container because it is deployed on its own, as static objects behind the edge, and talks only to the API.

## 2  Building block

### 2.1  Component Diagram

The components below are the boxes of this container's component diagram, which is not yet drawn. The outside view of this block is its box in [AP-001](../../patterns/AP-001-ontology-driven-graphrag/index.md) and the row of its SBB in [RA-001](../../patterns/RA-001-knowledge-store-on-aws/index.md).

### 2.2  Components

- **Chat.** The question, history, claims, sources, gaps and steps as they stream
- **Workbench panel.** Steps, prices, term usage and requests, for curators
- **Ontology page.** The active version and its terms
- **Sign-in and embed.** Code flow with PKCE against the identity provider, or the host's site grant and the embed protocol
- **Common.** config.json, the brand, the token store

### 2.3  Attributes

- **No secrets.** A public client; the token is the reader's
- **Embeddable.** frame-ancestors names the host and the portal in site mode

### 2.4  Semantic

Inside: what is shown and how the reader is identified. Outside: every fact, which comes from the API.

### 2.5  Identity & Access Management

A public Cognito client with PKCE; in site mode the host's grant; the page holds nothing a reader could not see.

### 2.6  Observability

Edge access logs; the API's log carries the subject.

### 2.7  Governance & Policy Enforcement

Managed security headers at the edge; config.json written by Terraform decides the mode.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | request | A reader in a browser, signed in by code flow with PKCE or carried by a host website's grant (CT-016) |
| I2 | out | request | HTTPS /api calls with the access token or the site grant (CT-001) |

### 3.4  Capability dependencies (requires)

- ABB-019 (1): Everything it shows comes through the API
- ABB-020 (1): Signs the reader in, or carries the host's grant

## 4  Mapping

| Where | What |
|---|---|
| Code | `chat/index.html, app.js, common.js, ontology.html, ontology.js, styles.css; infra/modules/portal (site objects)` |
| Capabilities | CAP-009, CAP-012 |
| Context | BC-006 |

## 5  Solution Building Block guidance

Realised as objects in a private bucket served by CloudFront (SBB-018). The command line serves the same page locally (ABB-028).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain |
