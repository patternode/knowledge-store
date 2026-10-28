---
kind: sbb
id: SBB-018
title: "SBB-018 Chat page on CloudFront"
description: "The chat page as static objects in a private bucket served by CloudFront, with /api/* routed to the API behind the same distribution."
version: 0.2.0
status: active
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
realises: [ABB-018]
realised_by_services: [chat-page]
technologies:
  - { name: "Amazon CloudFront", vendor: "AWS", licensing: "pay per request" }
  - { name: "Amazon S3 (the site bucket)", vendor: "AWS", licensing: "pay per use" }
product_mapping:
  - { abb_component: "Chat, workbench panel, ontology page, common", technology: "index.html, app.js, common.js, ontology.html, ontology.js, styles.css and config.json as objects in the private site bucket (ST-012)" }
  - { abb_component: "Sign-in and embed", technology: "A public Cognito client with PKCE, or the host's grant with frame-ancestors naming the host (CT-016)" }
  - { abb_component: "Edge", technology: "A distribution, PriceClass_100, origin access control, the origin secret header to the API, managed security headers, an optional custom domain and web ACL (DN-009)" }
cloud_provider: aws
deployment_model: managed
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# SBB-018 Chat page on CloudFront

| Property | Value |
|---|---|
| SBB ID | SBB-018 |
| Realises | ABB-018 |
| Realised by services | chat-page |
| Products | Amazon CloudFront; Amazon S3 (the site bucket) |
| Cloud | aws, managed |
| Status | active, as deployed at 0.3.0, recalibrated to container grain |

The chat page as static objects in a private bucket served by CloudFront, with /api/* routed to the API behind the same distribution.

## 1  Purpose

One origin for the page and the API removes cross-origin configuration and puts the origin secret between the edge and the function; static objects need no server.

## 2  Building block

| ABB component | Realised by |
|---|---|
| Chat, workbench panel, ontology page, common | index.html, app.js, common.js, ontology.html, ontology.js, styles.css and config.json as objects in the private site bucket (ST-012) |
| Sign-in and embed | A public Cognito client with PKCE, or the host's grant with frame-ancestors naming the host (CT-016) |
| Edge | A distribution, PriceClass_100, origin access control, the origin secret header to the API, managed security headers, an optional custom domain and web ACL (DN-009) |

## 3  Operation

config.json is written by Terraform and decides local, hosted or site mode; a deploy invalidates the distribution.

## 4  Cost

Per request; cents.

## 5  ABB traceability

ABB-018. The decisions behind the choice are in [../../decisions](../../../decisions/README.md); the reference architecture that composes this block with the others is RA-001.

## 6  Revision history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-16 | Reversed from the implementation |
| 0.2.0 | 2026-10-17 | Recalibrated to container grain; new in the calibration |
