# Architecture

The architecture of Knowledge Store, expressed with the [architecture continuum](https://github.com/dermot-obrien/architecture-continuum/blob/main/docs/continuum.md) and kept here, in the component's own repository, beside its implementation. It is reversed from the implementation at release 0.3.0: every page names the code that holds it today, and the findings where the code and the continuum's rules differ are recorded rather than hidden. How to install it on AWS is the [deployment guide](../deploy/aws/README.md).

## The map

The folders follow the continuum's three spaces, plus decisions. A register (CSV) is the index of each kind; a page is the record of each element. Identifiers are this catalogue's, namespace `ks`, so another catalogue cites them as `ks:SV-001`.

| Where | What | Identifiers |
|---|---|---|
| [platform.md](platform.md) | PL-001 Knowledge Store: what it provides, owns and contains | PL |
| [landscape.md](landscape.md) | Where the platform sits: what it consumes, who consumes it | |
| [demand/](demand/) | The demand space: [domains](demand/domains.md), [outcomes](demand/outcomes.csv), [use cases](demand/use-cases/README.md), [capabilities](demand/capabilities/README.md), the [product](demand/product.md) and its [features](demand/features.csv) | OC, UC, CAP, PRD, FE |
| [solution/](solution/) | The solution space: [bounded contexts](solution/contexts/README.md), [architecture building blocks](solution/abbs/README.md), [solution building blocks](solution/sbbs/README.md), [patterns](solution/patterns/README.md) and [contracts](solution/contracts.csv) | BC, ABB, SBB, PAT, REF, CT |
| [runtime/](runtime/README.md) | What runs where: [services](runtime/services.csv), [nodes](runtime/nodes.csv) and [stores](runtime/stores.csv) | SV, DN, ST |
| [decisions/](decisions/README.md) | Decision records and open considerations | ADR, CN |
| [registers/](registers/) | The identifier series and the namespaces, for the cross-reference skill | |

The design notes that predate the catalogue stay in place and carry the reasoning the registers point at:

| Note | What it covers |
|---|---|
| [Knowledge Store on AWS](aws/aws.md) | The reference architecture's narrative: ingestion, chat, grounding, valves, evaluation, costs, the two applies. REF-001 is its register form |
| [Graph and document backends](aws/backends.md) | Optional Neo4j, Apache AGE and MongoDB projections behind the same API (ADR-008, SBB-011) |
| [Structured lookup](aws/structured.md) | A mapped table beside the documents, so an answer can cite a cell (ADR-009, CN-003) |
| [Security design](security.md) | How the design keeps people, data and spend safe (ADR-002, ADR-003, the controls of REF-001) |
| [Source controls](source-controls.md) | How a document's permissions, protection and classification travel with its passages (CN-002, ADR-010) |
| [Scalability](aws/scalability.md) | What limits each part as a collection grows; Neptune against Neo4j (CN-001) |
| [Diagram](aws/architecture.png) | The reference architecture, also as [SVG](aws/architecture.svg), [draw.io](aws/architecture.drawio) and its generator [architecture.py](aws/architecture.py) |

## Reading it end to end

From the top: PL-001 owns three outcomes (OC-001 answers a reader can check, OC-002 an ontology the organisation owns, OC-003 a store run at a visible cost). Nine use cases realise them, each written before any design in the use-case skill's form, each fulfilled by features of PRD-001 and realised by the pattern. Thirteen capabilities say what must be possible; eight bounded contexts say where each model lives; twenty-three architecture building blocks are the logical parts, each inside one context; fourteen solution building blocks name the technologies; PAT-001 is the logical pattern and REF-001 its physical form on AWS; nine services are the deployables, on sixteen nodes, with eighteen stores each owned by one context; ten decisions and six considerations say why, and what is still open.

From the bottom: pick a service in [runtime/services.csv](runtime/services.csv), follow `realises` to its SBB, `part_of` to its context, the context's `realises_capabilities` to the capabilities, and the capability's `required_by_outcomes` to the outcome. Every link is a field in front matter the skills validate.

## What the continuum exposed

| Finding | Where it is recorded |
|---|---|
| The pipeline image composes four contexts and the portal Lambda three; the continuum says a service serves one | CN-006, with the smallest step that satisfies the rule for answering |
| Two import cycles cross the context boundary between the tools and the portal's index | BC-004, BC-006, SV-003, SV-004 |
| The portal's fallback answering loop does not meet ADR-002 (no claim-level check) | BC-005, ADR-002 |
| Contracts were published nowhere as a list | [solution/contracts.csv](solution/contracts.csv), sixteen of them |
| Two log groups are outside Terraform | SV-006, CAP-013 |
| An explorer page under `portal/` is in the repository, not deployed, and sends a different token | SV-007, SV-003 |

## Conventions

- Front matter follows the continuum's [front matter standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/standard-frontmatter.md) and validates against its schemas; `.agents/skill-bindings.toml` binds each kind's folder for the skills.
- Prose: no em dashes inside sentences, no bold inside sentences, British spelling, one paragraph per line (the repository's CONTRIBUTING.md).
- Dates are the date the page was reversed, not the date the decision was made; `provenance.review_state` is `ai-raw` until a person reviews a page.
- Identifiers in body text are plain; the cross-reference skill turns them into links where a site renders them.

## Diagrams and decks

Each use case and pattern is also a model: the `model` skill reads its Participants, Interactions, Interfaces and Scenarios tables, emits `components.drawio` beside it, validates the diagram against the document, stamps the exported `components.svg` (the `.render.json` is its record) and, for a use case, animates `scenarios.html`. The `pattern` skill's `publish.py` runs the same steps for a folder and builds a deck under `dist/`, which is ignored. After editing a table, run from the repository root:

```bash
python3 .agents/skills/pattern/scripts/publish.py docs/architecture/demand/use-cases --recursive --render never --no-pdf
python3 .agents/skills/pattern/scripts/publish.py docs/architecture/solution/patterns --recursive --render never --no-pdf
```

The skills are installed by `node <ai-assisted-work>/bin/skills.mjs sync` from `.agents/skills.json`; `markdown-deck` needs `npm install` in its folder once. The first layout of a diagram is by rank and is meant to be refined by hand in draw.io, then re-exported and stamped (`model.py stamp components.svg --diagram components.drawio --layer Structure`).
