---
kind: sbb
id: SBB-016
title: "SBB-016 Chat page on CloudFront and S3"
description: "The static chat page and ontology page as objects in a private bucket served through CloudFront, on the same URL as the API, with no build step and no external scripts."
version: 0.1.0
status: active
created: 2026-10-17
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-018]
realised_by_services: [chat-page]
products:
  - { name: "Amazon CloudFront", vendor: "AWS", licensing: "per request" }
  - { name: "Amazon S3", vendor: "AWS", licensing: "pay per use" }
product_mapping:
  - { abb_component: "Site bucket", sbb_product: "A private bucket of index.html, app.js, common.js, ontology.html, ontology.js, styles.css, config.json and brand/*, read through origin access control, no-cache" }
  - { abb_component: "Edge", sbb_product: "CloudFront with managed security headers, an optional web ACL and custom domain; /api/* routed to the API (SBB-007) with an origin secret header" }
  - { abb_component: "Configuration", sbb_product: "config.json written by Terraform: the API base, the sign-in mode and the identity pool or site keys" }
  - { abb_component: "Brand", sbb_product: "Files under brand/ only, so a deployment can be reskinned without touching the page" }
cloud_provider: aws
deployment_model: managed
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-016 Chat page on CloudFront and S3

| Property | Value |
|---|---|
| SBB ID | SBB-016 |
| Realises | ABB-018 |
| Realised by services | chat-page |
| Products | Amazon CloudFront; Amazon S3 |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0; added in the recalibration of 2026-10-17 |

The static chat page and ontology page as objects in a private bucket served through CloudFront, on the same URL as the API, with no build step and no external scripts.

## 1  Purpose

A page with no build step and no external scripts is auditable by reading it, deploys as an object copy, and costs nothing idle; sharing the distribution with the API keeps one origin for the browser.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Site bucket | A private bucket of index.html, app.js, common.js, ontology.html, ontology.js, styles.css, config.json and brand/*, read through origin access control, no-cache |
| Edge | CloudFront with managed security headers, an optional web ACL and custom domain; /api/* routed to the API (SBB-007) with an origin secret header |
| Configuration | config.json written by Terraform: the API base, the sign-in mode and the identity pool or site keys |
| Brand | Files under brand/ only, so a deployment can be reskinned without touching the page |

## 3  Operation

Objects are written on apply; CloudFront is invalidated by the module; a host website embeds the page under the site grant (CT-011, CT-016).

## 4  Cost

Per request; close to nothing idle.

## 5  ABB traceability

ABB-018. The page container, split from the former portal SBB so that the page and the API are one block each. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the physical pattern that composes this block with the others is REF-001.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-17 | Added in the recalibration to container grain |
