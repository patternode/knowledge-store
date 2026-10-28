---
kind: product
id: PRD-001
title: "PRD-001 Knowledge Store"
status: draft
version: 0.1.0
created: 2026-10-16
last_modified: 2026-10-16
owner: "Patternode (Dermot O'Brien)"
platform: PL-001
team: "Patternode"
runs: [pipeline, chat-agent, portal-api, tools-graph, tools-passages, agent-interceptor, chat-page, knowledge-store-cli, evaluation-runner]
---

# PRD-001 Knowledge Store

The product is the store as shipped: the repository's release, which a consumer deploys as one Terraform module and uses through the chat page, the API, the tools and the CLI. It is what a consumer is offered, where the platform is what a team owns and runs; here they coincide, which is the usual case for a standalone component. The product's unit of behaviour is a feature, something it does that its users value, and the register of them is [features.csv](features.csv). A use case is fulfilled by features; a feature is implemented by services; an improvement is a change to a feature, and the pull request that carries it is the change record.

| Field | Value |
|---|---|
| Product | PRD-001 Knowledge Store |
| Offered by | PL-001 |
| Consumers | Any organisation deploying the module, including a host application that pins a release |
| Released as | A git tag `vX.Y.Z` of this repository, which the module source pins |
| Versions | 0.1.0 (the core), 0.1.1, 0.1.2, 0.2.0 (the chat agent, valves, evaluation, structured lookup, the AWS reference deployment), 0.3.0 (branding) |

## Features

| Feature | What the product does | Fulfils | Implemented by |
|---|---|---|---|
| FE-001 Grounded answers | Every shown statement cites a passage with a quote, or a cell or figure, checked by code | UC-001 | SV-002, SV-003 |
| FE-002 Stated abstention | When the sources cannot answer, says so and what was missing | UC-001 | SV-002 |
| FE-003 Bring your own ontology | A provided Turtle master published and activated by configuration | UC-003 | SV-001 |
| FE-004 Ontology discovery with review | A first draft from a sample, reviewed, with its evidence | UC-004 | SV-001 |
| FE-005 Classified versions | Immutable versions; the bump says what changed; delta extraction after an additive one | UC-003, UC-004, UC-005 | SV-001, SV-008 |
| FE-006 Candidates and proposals | Terms extraction could not place, proposed as the next minor version | UC-005 | SV-001, SV-008 |
| FE-007 Structured lookup | Mapped tables beside the documents; cells and figures cited and recomputed | UC-006, UC-001 | SV-001, SV-004, SV-002 |
| FE-008 Passage search by meaning | A vector per passage; the hit is a passage id | UC-001 | SV-001, SV-005 |
| FE-009 Graph tools | Entities, neighbourhoods and paths in the ontology's terms, read only | UC-001 | SV-004 |
| FE-010 The workbench | Steps as they happen, cost, term usage, what it would take, ontology requests | UC-001, UC-005 | SV-002, SV-003, SV-007 |
| FE-011 The ontology page | The active ontology as a graph with counts, tiers and a question overlay | UC-001 | SV-007, SV-003 |
| FE-012 Scope | Public and private sources, enforced at every hop | UC-008 | SV-003, SV-006, SV-004, SV-005 |
| FE-013 Sign-in through a host website | A framed page and a short grant in place of the deployment's own sign-in | UC-008 | SV-003, SV-007 |
| FE-014 Valves and quotas | Per-question limits, daily counts, concurrency, throttle | UC-001 | SV-002, SV-003 |
| FE-015 Budget alert | A monthly budget mailed at 80 percent | UC-009 | infrastructure |
| FE-016 Evaluation sets | Questions with expected facts, scored deterministically | UC-007 | SV-009 |
| FE-017 One-stack deployment | One module, images built in the account, two applies | UC-009, UC-002 | infrastructure |
| FE-018 Launch stack | CloudFormation running the same Terraform | UC-009 | infrastructure |
| FE-019 Branding | Name, mark, colours, stylesheet, domain | UC-009 | SV-007 |
| FE-020 Optional backends | Neo4j or Apache AGE as the graph projection, MongoDB as the document projection and chat state | UC-002 | SV-001, SV-003 |
| FE-021 Local run | A folder as the lake, the Anthropic API, the local portal server | UC-009 | SV-008, SV-003 |
| FE-022 Source adapters | S3 uploads, local folders, HTTPS URLs, and your own through an entry point | UC-002 | SV-001 |
| FE-023 Idle at nothing | Pay-per-use services; the graph instance the one fixed cost, switchable | UC-009 | infrastructure |
| FE-024 Document and table links | A signed link to the original or the bound snapshot, after the scope check | UC-008, UC-001 | SV-003 |

## Improvements

A change to a feature is an improvement. This repository tracks them as issues and pull requests, with the pull request title as the changelog line (CONTRIBUTING.md, Releases); there is no separate improvement register. A consuming application keeps its own improvements in its own records.
