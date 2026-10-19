---
title: "Target-state view by subdomain"
---

# Target-state view by subdomain

An investigation: how the architecture in [docs/architecture](../architecture/README.md) can produce a view of the domain and its subdomains as the target state, each subdomain mapped down the continuum and overlaid with numbers a brainstorming session can point at, to decide which patterns to elaborate next. It answers six questions, recommends a method, and lists what the method would need. The working prototype is [scripts/target-state.mjs](../../scripts/target-state.mjs), and what it generates is the [target-state page](../architecture/target-state.md).

## Summary

The continuum already holds most of what the view needs. It names domain and subdomain in its vocabulary, every bounded context carries `subdomain_kind`, and every link from a context down to its services is a field in front matter. What it does not hold is the subdomain itself: a named piece of demand with a kind, mapped to the context or contexts that meet it. In Knowledge Store that lives only in the prose table on the [domain page](../architecture/demand/domains.md), which the prototype has to parse. The recommendation is a subdomain register in the demand space, a `map` flow in the continuum's `architecture` skill that draws the view from the pages and takes every stage from the existing stage flow, and this repository as its worked example.

The prototype shows the method works on real data and finds real breaks. Every capability in Knowledge Store is at R0, because the outcomes name their capabilities and no capability names its outcome, which is the side the stage tool reads; the continuum check passes all the same. Once that inverse is written, nine of the twelve L2 capabilities would hold R2 and three R1, and none reaches R3 while CN-006 and CN-001 are open. The view suggests eleven patterns to elaborate, led by domain-scoped architecture patterns for the Ontology and Extraction subdomains, whose contexts have no building block of their own.

## 1. Does the model already hold domains and subdomains?

Partly, and by design. The continuum's [vocabulary](https://github.com/dermot-obrien/architecture-continuum/blob/main/docs/continuum.md) defines a domain as the demand space and a subdomain as a part of it, core, supporting or generic, after Evans and Vernon, with Vernon's rule that a subdomain maps to a bounded context, ideally one to one. It then says a domain is not a folder or an identifier: it is recorded as `subdomain_kind` on each context and in the platform's purpose. The [bounded context standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/contexts/standard-bounded-context.md) has the same Subdomain Type field, and its schema enumerates `core`, `supporting` and `generic`. The front matter standard's DR-001 (platform replaces domain) and the vocabulary's first reconciliation (both words stay, with different jobs) settle why there is no domain folder. Knowledge Store's capabilities carry `subdomain_kind` as well.

| What the view needs | Held today | Where |
|---|---|---|
| The domain's name | In prose only | The platform's description; the first paragraph of the domain page |
| The subdomain as a named thing | In prose only | The table on the domain page |
| Its kind | Yes, but on the context, not the subdomain | `subdomain_kind` on each context and capability |
| What it needs, in demand terms | In prose only | The domain page's "What is needed" column |
| Subdomain to context, when not one to one | No | Nothing can say that two contexts meet one subdomain, or one context two |
| A subdomain with no context yet | No | A target state names demand before any context exists; there is nowhere to put it |
| A check | No | The continuum check does not read the domain page |

Three ways to fill the gap:

| Option | For | Against |
|---|---|---|
| Front matter on the context (`subdomain: { name, kind }`) | Smallest change; one place to edit | A subdomain with no context cannot exist, and two contexts meeting one subdomain repeat it; the demand space becomes a field of the solution space |
| A register in the demand space (`demand/subdomains.csv`, one row per subdomain with an identifier, name, kind, need and the contexts it maps to) | Demand stands on its own, so the target state can name a subdomain before it is solved; the mapping is checkable both ways; no page per subdomain is needed, the domain page stays the page | A new identifier series and a register to keep |
| Derived, one subdomain per context | Nothing to author | It makes the demand space a copy of the contexts, which removes the test the mapping exists for: whether the context boundary is right |

Recommendation: the register. It fits the continuum's rule that a domain is never a folder, because a register is not a folder, and it is the only option that lets the top of the target state be drawn before the contexts under it are settled. The context gains a `subdomains: [SD-NNN]` field as the inverse, and `subdomain_kind` is then derived from it rather than stated twice.

## 2. How a subdomain maps down, and where Knowledge Store's chain breaks

The chain is all front matter except its first link:

| From | To | Through |
|---|---|---|
| Subdomain | Bounded context | The domain page's table (to become the register) |
| Bounded context | Capability | `realises_capabilities` on the context |
| Capability | Outcome | `requires_capabilities` on the outcome; `required_by_outcomes` on the capability is the inverse the stage tool reads |
| Bounded context | ABB | `contains` on the context; `part_of` on the ABB |
| Capability | ABB | `realised_by_abbs` on the capability |
| ABB | SBB | `realised_by` on the ABB; `realises` on the SBB |
| Capability | Pattern | `realises` on the pattern, recognised by its signature, `kind: pattern` with a `pattern_type` |
| Bounded context | Service | `part_of` and `composes_contexts` on the service |
| Anything | Consideration | `affects` on the consideration |

The prototype walks it for each subdomain and records every break as a gap with the rule that found it. In Knowledge Store the chain breaks in six places:

1. Outcome and capability. The three outcomes name their capabilities; no capability names its outcome. The stage tool reads the capability's side, so all thirteen capabilities are R0. The continuum check reports no error, and the [architecture README](../architecture/README.md) describes walking the chain by `required_by_outcomes`, a field no page has. Separately, CAP-002, CAP-006 and CAP-007 are required by no outcome at all.
2. Context and building block. BC-002 Ontology and BC-003 Extraction contain no ABB: their models run inside ABB-024, which is part of BC-001. That is the calibration standard applied honestly (a context is a boundary of meaning, not a container), and the bounded context schema calls an empty context a gap, not an error. The view shows it as an ABB count of 0 own and 3 or 4 borrowed.
3. Capability and pattern. AP-001 and RA-001 are both scoped to the platform; no pattern is scoped to a subdomain. CAP-002, CAP-010, CAP-011, CAP-012 and CAP-013 are realised only by RA-001, so they reach a physical pattern with no logical one behind it.
4. Capability and consideration. CAP-008, CAP-011 and CAP-013 fail R2: no consideration affects them and they do not declare `open_questions: none`.
5. Register and page. The use-case register cites retired building blocks 22 times (ABB-015, ABB-006 and others) where the use-case pages were updated when they were folded. The check passes.
6. Service and consideration. SV-002 composes BC-005 and BC-004, and SV-008 composes five contexts, but CN-006 names neither. SV-008 is a command, and the continuum does not say whether its one-context rule applies to a command.

Two capabilities span three contexts each: CAP-007 Structured lookup (Ontology, Extraction, Knowledge graph) and CAP-010 Cost and spend control (Answering, People and access, Running it). Neither is a break, but no pattern says how the contexts divide the capability, and the view proposes one for each.

## 3. The logical view and the deployables view

They are distinct, and both come from the same pages by different relations. The logical view groups by `part_of` on the ABB and `realises_capabilities` on the context: subdomain, context, capability, building block. The deployables view groups by `part_of` and `composes_contexts` on the service. Neither needs anything the other does not have, so one generator draws both against the same numbered contexts and the distance between them is visible.

CN-006 is the test. Drawn as a matrix of services against contexts, SV-001 composes four contexts and SV-003 three, as CN-006 says, and the view adds two the consideration does not name: SV-002 and SV-008. Each option in CN-006 is a different deployables view over an unchanged logical view, which is the point of keeping them apart: the target state is the logical view, and the deployables are a projection of it that a decision chooses. So the view suggests drawing one reference architecture variant per option of CN-006 (P6), and choosing between drawn alternatives.

The logical view never shows a deployable as a box. It shows counts (services that are the context's own, and services that compose it besides), which is enough to see that every core context is composed into someone else's deployable.

## 4. The overlay: what it shows and where each number comes from

The reading in the brief holds once the material is in front of you: numbers people can point at, plus measures per box. The prototype draws three kinds:

| Number | Example | Source |
|---|---|---|
| Box number | 1 to 8, core subdomains first | The order of the subdomains, by kind |
| Gap reference | 3b | The box and the order of the gaps found in it |
| Pattern reference | P4 | The rank of a suggested pattern |
| Counts | ABB 0+4, SBB 0, AP 1, RA 1, SV 0+2, CN 1 | Front matter, by the chain in section 2 |
| Stage per capability | Six cells R1 to R6, and the stage held | The stage tool's `--json`: `rung` is held, `checks.Rn` empty is a pass |
| Lowest stage of the box | R0 | The lowest held by any of its capabilities |

The stage is the stage flow's and nothing else. The prototype runs the stage tool (in this repository still `aaa-rung`'s `rung.py`; `stage.py` in architecture-continuum v0.6) and reads its per-stage checks, so a cell is filled when the stage is held, shaded when its own check passes but a stage below fails (the standard's latent evidence), and empty when it fails. No second score is invented: the box shows the lowest held stage, because a subdomain is solved only when all its capabilities are.

What a gap means, as rules with codes the page and the JSON both use:

| Rule | Means |
|---|---|
| `no-context` | A subdomain with no bounded context: demand nobody has drawn a boundary for |
| `kind-mismatch` | The subdomain and its context disagree on core, supporting or generic |
| `no-abb` | The context's model has no container of its own; it runs in another context's building block |
| `no-demand` | A capability fails R1: it names no outcome on its page |
| `no-outcome` | A capability no outcome requires: the demand it answers is not recorded |
| `unbounded` | A capability fails R2 for its own reasons, such as no consideration and no `open_questions: none` |
| `open-consideration` | An open consideration affects the context, its capabilities or its building blocks; R3 waits on it |
| `no-architecture-pattern` | A capability reached only by a reference architecture, with no logical pattern behind it |
| `platform-scope-only` | Only platform-scoped patterns realise the subdomain's capabilities |
| `no-sbb` | A building block of the context with no active SBB, so R4 cannot hold |
| `no-service` | No deployable is the context's own |
| `service-spans-contexts` | A deployable that is or composes this context also composes others, with the consideration that names it, if any |
| `register-drift` | A register says something the pages no longer do |

A rule this prototype does not yet apply, and the method should: an ABB that is a box in no pattern, read from the patterns' Building Blocks tables.

Other readings of "numbers" were considered. A pattern's priority and target quarter are numbers a session would want, and they belong to the pattern portfolio (thread t-vq6): the view reads a `portfolio` block on a pattern when one exists and lists it, and none does yet. Workload numbers (volumes, cost, the outcomes' KPI targets) would make a second overlay worth having later, once the outcomes carry measured values rather than targets. A sequence (what to solve first) is what the ranked suggestions are.

## 5. Rendering

| Option | For | Against |
|---|---|---|
| A generated page in the Docusaurus site, with an SVG | Readable by anyone the site reaches; printable; regenerated on build like the diagrams; the numbered tables are the record | Not editable in a session |
| A generated draw.io with layers, through the `model` skill | Editable; the overlay on its own layers (structure, numbers, gaps) so a session can hide it or draw over it; the model skill's identifier contract survives copy and paste | The model skill reads one document's tables into one diagram; this view is a projection across the catalogue, which its contract does not cover today |
| A deck through markdown-deck | A session can walk one box per slide | A dense map does not suit a slide, and the deck is only as good as the page it is made from |

Recommendation: the page and its SVG as the record, and the draw.io as the working copy for a session, both generated in one run. The prototype writes both, plus the JSON a tool would read. For a session without a screen, the fallback is the SVG printed at A3 with the numbered tables beside it: every box, gap and suggestion has a reference, so people can annotate paper and the notes map back. The draw.io is written directly by the prototype; for the method it should come from the `model` skill, which needs a view mode (a graph and layers in, a stamped diagram out) to do it. A deck is a later, cheap addition: mark the generated page `deck_publish: true` with a slide per box.

## 6. Where the method lives

| Option | For | Against |
|---|---|---|
| A new flow of the continuum's `architecture` skill, `map` | It is a view over the whole continuum, and it reuses the stage flow, the bindings and the check in process | A new flow to maintain |
| Part of the pattern portfolio (t-vq6) | The output is a list of patterns to elaborate | Most gaps are not about patterns (outcomes, contexts, considerations, registers), and the portfolio records decisions about patterns rather than finding them |
| A script in this repository | Done; proves the idea | Every repository on the continuum would copy it |

Recommendation: the generic method as a `map` flow of the `architecture` skill (not `landscape`, which the continuum already uses for the layers of platforms), with Knowledge Store as its worked example. The flow proposes; the portfolio records. A suggestion from the map becomes a placeholder in the portfolio with its `realises` and the gap references it would close, and the portfolio's priority and state come back onto the map. This repository keeps `scripts/target-state.mjs` until the flow exists, then replaces it with a call to the skill, as `scripts/check-architecture.mjs` does for the check.

This note stays here, because its findings are about Knowledge Store's data. The method proposal in sections 1, 4, 5 and 6 and the list below should move to the architecture-continuum repository as a consideration when the follow-up starts, citing this page as the worked example.

## The prototype

`npm run target-state` (or `node scripts/target-state.mjs`) reads every page under docs/architecture, the subdomain table on the domain page, and the registers for the building blocks folded into others; runs the stage tool for every capability's checks; and writes, beside the landscape page:

| File | What |
|---|---|
| [target-state.md](../architecture/target-state.md) | The numbered map, the stage of each capability, the gaps with their rules, the patterns to elaborate next, and the deployables |
| [target-state.svg](../architecture/target-state.svg) | The logical view: subdomain boxes in core, supporting and generic bands, each with its context, its capabilities on the ladder, its counts and its gap references |
| [target-state-deployables.svg](../architecture/target-state-deployables.svg) | The services against the same numbered contexts |
| [target-state.drawio](../architecture/target-state.drawio) | Both views, editable, with the numbers and the gaps on their own layers |
| [target-state.json](../architecture/target-state.json) | The derived model |

`--check` exits 1 when the committed files are stale. The build regenerates them (`scripts/regenerate.mjs`), and like every other step there, the script skips in one line when the stage skill is not installed, so a clone without the skills builds the same site.

It reads patterns by signature (`kind: pattern` and `pattern_type`), never by name or folder, so the pattern portfolio's placeholders will count as soon as they exist. It parses the domain page's table, which is the weakest link and the first thing the register would replace.

## Patterns it suggests elaborating next

From the generated page at the time of writing; the page is the current list.

| Ref | Pattern | Why |
|---|---|---|
| P1 | Ontology as a domain-scoped architecture pattern (CAP-003, CAP-007) | BC-002 has no building block of its own; naming them is the logical half of CN-006 |
| P2 | Extraction as a domain-scoped architecture pattern (CAP-004, CAP-007) | The same for BC-003 |
| P3 | Knowledge graph as a domain-scoped architecture pattern (CAP-005, CAP-006, CAP-007) | Where CN-001 and CN-006 are argued in boxes |
| P4 | Answering as a domain-scoped architecture pattern (CAP-008, CAP-010, CAP-012) | CAP-010 and CAP-012 have no logical pattern |
| P5 | Structured lookup across Ontology, Extraction and Knowledge graph (CAP-007) | One capability in three contexts, and nothing says how they divide it |
| P6 | The deployables of the target state, one reference architecture variant per option of CN-006 | So CN-006 is decided between drawn alternatives |
| P7 | Cost and spend control across Answering, People and access, and Running it (CAP-010) | The same shape as P5 |
| P8 to P11 | Domain-scoped patterns for the supporting and generic subdomains | Lower weight; P10 and P11 cover CAP-011 and CAP-013, which have no logical pattern |

The ranking puts core subdomains first and then counts the gaps a pattern would close. It is a starting point for the session, not a priority.

## What the method would need

For a follow-up; none of it is made here.

The continuum's standard:

1. A subdomain register in the demand space, with an identifier series (for example `SD-NNN`), name, kind, need, the domain, and the contexts it maps to; `subdomains` on the bounded context as the inverse, with `subdomain_kind` derived from it. Update the vocabulary's reconciliation to say a register is how a domain is recorded without a folder.
2. A view standard for the target state: the logical view and the deployables view, the numbering (box, box and letter, P and number), the gap rules with their codes, and what each means.
3. The check to enforce the inverse of `requires_capabilities` on the outcome and `required_by_outcomes` on the capability, or the stage flow to read either side. Today a catalogue can pass the check with every capability at R0.
4. The check to compare a register's relation columns with its pages (the use-case register's drift).
5. A rule on whether a capability's `subdomain_kind` must agree with the contexts that realise it, or the field removed from the capability.
6. A statement of whether the one-context rule applies to a service of `kind: command`, and a check that an open consideration about deployables names every service that composes more than one context.

The `architecture` skill:

7. A `map` flow: reads the subdomain register and the existing bindings, calls the stage engine in process, writes the page, the SVG, the draw.io and the JSON, and has a `--check` for staleness.
8. Stable codes on the stage flow's blockers in `--json`, beside the English text, so the map classifies a blocker without matching words.
9. The gap rule this prototype lacks: an ABB that is a box in no pattern.

The pattern skills:

10. The `pattern` skill: a `subdomains` field for `pattern_scope: domain`, so a domain-scoped pattern lands on its box; and creating a placeholder from a map suggestion, carrying `realises` and the gap references.
11. The pattern portfolio (t-vq6): read by the map, and fed by it.
12. The `model` skill: a view mode that takes a graph and named layers and emits a stamped draw.io, so the map's diagram is the model skill's.
13. markdown-deck, optionally: a slide per box from the generated page.

Knowledge Store's own data, for a separate change (none of it is the method):

14. `required_by_outcomes` on each capability, and an outcome for CAP-002, CAP-006 and CAP-007, or a `demand_assumption`.
15. A consideration or `open_questions: none` for CAP-008, CAP-011 and CAP-013.
16. The use-case register refreshed from its pages.
17. CN-006's `affects` to name SV-002 and SV-008, or say why not.
18. The migration to architecture-continuum v0.6.1 (thread t-c6t), after which the prototype reads `stage.py` instead of `rung.py`; it already prefers `stage.py` when installed, and reads `stage` before the former `rung` key.
