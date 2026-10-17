---
kind: abb
id: ABB-018
title: "ABB-018 Chat page"
short_name: "PAGE"
description: "A static page with no build step and no external scripts: the chat with claims, sources, highlighted quotes and cells, the workbench, demonstrate mode, and the ontology page with its question overlay."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
category: "Portal"
part_of: BC-006
realises_capabilities: [CAP-009, CAP-012]
realised_by: [SBB-007]
requires:
  - { abb: ABB-019, cardinality: "1", rationale: "The API it calls" }
  - { abb: ABB-020, cardinality: "1", rationale: "Sign-in" }
domains: [application]
interfaces:
  - { id: "I1", direction: "in", type: "request", description: "A person's question, collection choice, mode" }
  - { id: "I2", direction: "out", type: "request", description: "The HTTP API (CT-001); the embed protocol with a host website (CT-016)" }
  - { id: "I3", direction: "in", type: "request", description: "config.json: mode, sign-in endpoints, brand" }
mandatory_subabbs: [iam, observability, governance]
cross_cutting: false
references:
  - { type: source, repo: "patternode/knowledge-store", path: "chat/index.html, app.js, common.js, ontology.html, ontology.js, styles.css", ref: "main" }
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
| Version | 0.1.0 |
| Status | draft, reversed from the implementation at 0.3.0 |
| Category | Portal |
| Bounded context | BC-006 |
| Realises | CAP-009, CAP-012 |
| Realised by | SBB-007 |

A static page with no build step and no external scripts: the chat with claims, sources, highlighted quotes and cells, the workbench, demonstrate mode, and the ontology page with its question overlay.

## 1  Purpose

The page is where grounding becomes visible: a citation opens the passage with the words highlighted. Keeping it static and dependency-free keeps its security policy strict and its branding a file.

## 2  Building block

### 2.1  Component Diagram

The components below are the diagram's boxes; the draw.io is not yet drawn. The outside view of this block is its row in [REF-001](../../patterns/REF-001-knowledge-store-on-aws/index.md).

### 2.2  Fundamental functionality

- **Chat.** Ask and what-would-it-take modes; answers from claims; sources panel; document and table links
- **Workbench panel.** Steps, cost, ontology used, this session
- **Ontology page.** D3 force graph with tiers, counts, declared and observed relations, overlay
- **Common.** DOM builder without innerHTML, config, sign-in modes, API client, brand under brand/ only

### 2.3  Attributes

- **Security.** CSP self only, no inline code, no innerHTML, frame-ancestors only in site mode
- **Brandability.** brand.css, logo and icon written by Terraform beside the page

### 2.4  Semantic

Inside: the pages. Outside: the API and sign-in.

### 2.5  Identity & Access Management

Tokens in sessionStorage; a 401 triggers one refresh.

### 2.6  Observability

None beyond the browser.

### 2.7  Governance & Policy Enforcement

CloudFront security headers; no-cache so a page never runs an old script.

## 3  Interfaces

| Interface | Direction | Type | Description |
|---|---|---|---|
| I1 | in | request | A person's question, collection choice, mode |
| I2 | out | request | The HTTP API (CT-001); the embed protocol with a host website (CT-016) |
| I3 | in | config | config.json: mode, sign-in endpoints, brand |

### 3.4  Capability dependencies (requires)

- ABB-019 (1): The API it calls
- ABB-020 (1): Sign-in

## 4  Mapping

| Where | What |
|---|---|
| Code | `chat/index.html, app.js, common.js, ontology.html, ontology.js, styles.css; infra/modules/portal (site objects)` |
| Capabilities | CAP-009, CAP-012 |
| Context | BC-006 |

## 5  Solution Building Block guidance

Realised as S3 objects behind CloudFront (SBB-007); served locally by the local server (SBB-013).

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
