---
kind: bounded-context
id: BC-006
title: "BC-006 Portal and identity"
description: "People, sessions, scope, quotas and the chat page: who may ask, who may read what, and the page and API they do it through."
version: 0.1.0
status: draft
created: 2026-10-16
last_modified: 2026-10-17
owner: "Patternode (Dermot O'Brien)"
lifecycle_state: baseline
part_of: PL-001
contains: [ABB-018, ABB-019, ABB-020]
realises_capabilities: [CAP-009, CAP-010]
subdomain_kind: supporting
c4_levels: [container, component]
ubiquitous_language:
  - { term: "Person", definition: "A signed-in caller with a sub, groups or roles; the agent acts only as the person" }
  - { term: "Private reader", definition: "A person in the private-readers group, with a private role of the host website, or an application with the tools.private scope" }
  - { term: "Grant", definition: "A short ES256 token a host website hands a framed page, verified against configured keys" }
  - { term: "Service client", definition: "A client-credentials identity the portal uses in site mode, public or private, scoped to what its people may read" }
  - { term: "Quota", definition: "Questions per person per day, counted with a conditional write" }
  - { term: "Chat state", definition: "An answer, its steps while it runs, the quota counters and the usage totals" }
  - { term: "Origin check", definition: "The secret header CloudFront adds, without which the API refuses" }
  - { term: "Document link", definition: "A signed URL to the original or a bound table, issued after the scope check, for ten minutes" }
relationships:
  - { with: BC-005, pattern: customer-supplier, role: upstream }
  - { with: BC-004, pattern: shared-kernel, role: downstream }
  - { with: BC-008, pattern: conformist, role: downstream }
provenance:
  origin: ai-generated
  review_state: ai-raw
---

# BC-006 Portal and identity

| Property | Value |
|---|---|
| Context ID | BC-006 |
| Platform | PL-001 Knowledge Store |
| Owner team | Patternode (Dermot O'Brien) |
| Subdomain | supporting |
| Realises | CAP-009, CAP-010 |
| Contains | ABB-018, ABB-019, ABB-020 |

People, sessions, scope, quotas and the chat page: who may ask, who may read what, and the page and API they do it through.

## Ubiquitous language

| Term | Meaning in this context |
|---|---|
| Person | A signed-in caller with a sub, groups or roles; the agent acts only as the person |
| Private reader | A person in the private-readers group, with a private role of the host website, or an application with the tools.private scope |
| Grant | A short ES256 token a host website hands a framed page, verified against configured keys |
| Service client | A client-credentials identity the portal uses in site mode, public or private, scoped to what its people may read |
| Quota | Questions per person per day, counted with a conditional write |
| Chat state | An answer, its steps while it runs, the quota counters and the usage totals |
| Origin check | The secret header CloudFront adds, without which the API refuses |
| Document link | A signed URL to the original or a bound table, issued after the scope check, for ten minutes |

## Where the model lives today

- `portal_api/handler.py, state.py, agent_client.py, local.py (routes, chat state behind one port, the Runtime client, the local server)`
- `site_grant.py, claims.py, tools/interceptor.py (the host website's grant; the scope rule; the Gateway interceptor that applies it)`
- `chat/ (the chat and ontology pages), portal/ (the earlier explorer page, not deployed by the module)`

The handler routes everything behind one Lambda, dispatching answers to itself asynchronously; the interceptor is deployed beside the Gateway but applies this context's rule. The explorer page under portal/ is in the repository and not in the module.

## Relationships with other contexts

| With | Pattern | Role | Why |
|---|---|---|---|
| BC-005 | customer-supplier | upstream | Dispatches the question and keeps the answer |
| BC-004 | shared-kernel | downstream | Serves the index-backed routes from the same index module the tools use |
| BC-008 | conformist | downstream | Model access for the fallback loop |

## Building blocks

ABB-018, ABB-019, ABB-020; each is a page under [../abbs](../../abbs/README.md). Each is one C4 container; what runs inside it is listed on its page.
