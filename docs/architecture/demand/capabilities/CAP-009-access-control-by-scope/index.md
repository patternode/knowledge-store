---
kind: capability
id: CAP-009
title: "CAP-009 Access control by scope"
description: "Deciding who may ask and who may read private content, with the person's verified identity carried through every hop and the scope rule applied at each one."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
level: L2
parent: CAP-001
components:
  organisation: "The administrator creates users and groups; a host website may sign people in instead"
  people: ["Administrators", "Readers", "A host website's operator"]
  processes:
    - "Sign in with Cognito (code flow with PKCE) or present a site grant"
    - "Carry the token to the Runtime and the Gateway; the interceptor sets caller_private"
    - "Filter every view, tool result, retrieval and document link by scope"
    - "Sign document and table links only after the scope check, for ten minutes"
  technology: "Cognito user pool, groups and resource-server scopes; ES256 site grants verified with the standard library; the Gateway interceptor; the scope function in claims.py"
maturity:
  current: 4
  target: 4
  assessment_date: 2026-10-16
  assessor: "Patternode (Dermot O'Brien), reversed from the implementation"
subdomain_kind: supporting
provided_by_platform: PL-001
realised_by_abbs: [ABB-020, ABB-027, ABB-026, ABB-012, ABB-025, ABB-019, ABB-018]
gaps:
  - "Scope is one boolean per source; the controls a document carries of its own are designed, not built (CN-002)"
  - "The portal page sends the ID token where the chat page sends the access token"
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# CAP-009 Access control by scope

| Property | Value |
|---|---|
| Capability ID | CAP-009 |
| Level | L2 |
| Parent | CAP-001 |
| Status | Draft, reversed from the implementation at 0.3.0 |
| Subdomain | supporting |
| Maturity | 4, target 4 |
| Realised by | ABB-020, ABB-027, ABB-026, ABB-012, ABB-025, ABB-019, ABB-018 |

Deciding who may ask and who may read private content, with the person's verified identity carried through every hop and the scope rule applied at each one.

## 1  Purpose

Nothing between the browser and the data acts with more rights than the person. One rule says what private means; it is read from the token at the portal, the agent and the tools, and the interceptor overwrites whatever the model asked for.

## 2  Capability definition

| Dimension | For Knowledge Store |
|---|---|
| Organisation | The administrator creates users and groups; a host website may sign people in instead |
| People | Administrators, Readers, A host website's operator |
| Processes | Sign in with Cognito (code flow with PKCE) or present a site grant; Carry the token to the Runtime and the Gateway; the interceptor sets caller_private; Filter every view, tool result, retrieval and document link by scope; Sign document and table links only after the scope check, for ten minutes |
| Technology | Cognito user pool, groups and resource-server scopes; ES256 site grants verified with the standard library; the Gateway interceptor; the scope function in claims.py |

## 3  Sub-capabilities

| Sub-capability | What it covers | Status |
|---|---|---|
| Sign-in | Cognito hosted UI or a host website's grant | In place |
| Identity all the way down | The same token at every hop | In place |
| Scope enforcement | One rule, applied at each layer | In place |
| Document controls | Classification and entitlements from the source | Not started |

## 4  What the implementation does today

Public or private per source, applied in the index, the SPARQL queries, the backends, the Knowledge Base filter, the structured tools and the silver fallback. The private-readers group, the tools.private scope and the site's private roles are the three ways to be private.

## 5  Maturity

Current maturity is 4 on the 0 to 5 scale, read from the implementation: the capability is defined, built and in service in the Patternode lab and in any deployment of the module. Target 4.

## 6  Gaps

- Scope is one boolean per source; the controls a document carries of its own are designed, not built (CN-002)
- The portal page sends the ID token where the chat page sends the access token
