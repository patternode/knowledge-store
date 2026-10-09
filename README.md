# Knowledge Store

Put documents in a data lake and get an ontology-typed knowledge graph, and a chat in which an
agent answers questions from it, every statement linked to the passage it comes from, for any
domain. Bring an ontology, or have one discovered from the documents and reviewed. After that,
it is maintained under version control, released in controlled versions, and grown from the
terms extraction finds it lacks.

It runs on AWS, in one account from one Terraform stack, or on your own machine over a local
folder. Model calls go to Claude through Amazon Bedrock, so no data leaves your account, or to
the Anthropic API.

A short briefing of these concepts, with the video, is in [docs/explainer](docs/explainer/README.md).

## What it does

```
sources ──adapters──▶ bronze ──refine──▶ silver ──extract──▶ gold ──project──▶ portal
(S3 uploads,          immutable,         parsed text,        RDF per document     concepts,
 web pages,           content-           deterministic       per ontology         graph, chat
 your own adapter)    addressed          passages            version (the record)
                                              │                    ▲
                                              ▼                    │
                                  discover (no ontology yet) ─▶ draft ─▶ a person curates
                                              ▲                          and publishes a
                                  candidates (terms the ontology         version (immutable)
                                  lacks) ─▶ revision draft ──────────────┘
```

| Layer | Holds | Keyed by |
|---|---|---|
| landing/ | whatever people upload; never modified | the uploader's paths |
| bronze/ | one immutable copy of each distinct file, with where it came from | sha256 of the bytes |
| silver/ | parsed text and deterministic passages (the unit of citation) | document id |
| gold/&lt;version&gt;/ | SHACL-valid RDF per document at one ontology version: the system of record; plus candidates and the portal's projection | version, document id |
| ontology/ | published versions (master, renditions, manifest), drafts, the candidate register | semver |

The layers borrow the medallion names, but the design is a system of record plus projections.
The RDF in gold is the record. The portal's index, and any graph database you add, are
projections rebuilt from it. Gold is not a quality tier above silver. Extracted facts carry
more uncertainty than the text they came from, which is why every fact cites the passages it
was extracted from.

## The ontology lifecycle

### How an ontology is derived

A collection's ontology says what its documents are about. The profile (its name, description and key terms) steers the prompts that discover and extract. The core vocabulary (`ks:`, [docs/core-vocabulary.md](docs/core-vocabulary.md)) is shared by every deployment and records where a fact came from. Domain facts are typed only by the collection ontology.

It is derived in one of two ways.

**You bring it.** Set `ontology_dir` to a directory holding `ontology.ttl` (and optionally `shapes.ttl`). That Turtle file is the master. The sweep publishes the version its `owl:versionInfo` names and extracts against it. Discovery does not run. To change it, edit the file, bump `owl:versionInfo`, and apply.

**It is discovered from the documents**, when the collection has no ontology yet and at least `discovery.min_docs` documents (5 by default) have been refined. The method follows EDC (extract, define, canonicalise; Zhang and Soh, EMNLP 2024). Discovery reads a sample, so its cost is `discovery.sample` times `discovery.resamples`, whatever the size of the collection.

1. **Sample.** Up to `discovery.sample` documents (20), spread across sources, drawn `discovery.resamples` times (2). Each document contributes at most eight passages.
2. **Propose.** For each document the model names classes, relations and attributes, each with a definition and one to three examples copied from a passage. An example that does not appear in the passage it cites is dropped.
3. **Aggregate.** Proposals that normalise to the same name become one term. The term keeps how many sampled documents proposed it, and its stability, the share of samples that proposed it. The draft report also gives the Jaccard overlap of the type names across samples, because this induction varies from run to run.
4. **Consolidate.** One call turns that list into a small ontology: synonyms merged, a shallow hierarchy, a domain and range on every relation, a datatype on every attribute, and about `discovery.target_classes` classes (15). It records what it rejected and why.
5. **Review.** On by default (`discovery.review`). A second call sees the draft with each term's document support and returns edits only: a parent, a merge, a drop, or a corrected domain, range or datatype, each with a reason. The edits are applied in code. An edit that would create a cycle, or that names a term or a datatype the draft does not have, is skipped. The draft report lists what was applied and what was skipped, so a curator can undo any of them.

The draft is written to `ontology/drafts/<id>/` as `ontology.ttl`, `shapes.ttl` and `report.json`. With `ontology_mode = "curated"` a person edits it and publishes it. With `"auto"` the sweep publishes that draft as 0.1.0.

**Later versions come from what the active ontology could not say.** Extraction records candidate terms it had no class, relation or attribute for, with the passage text that stated them. Those candidates stay out of the graph. A curator can also keep a workbench report ("What would it take?") as an ontology request. `knowledge-store candidates --propose` sends both through consolidation again, with the current ontology in front of the model and an instruction to leave existing terms unchanged. A term is included when at least two documents named it, or when a request asked for it, and it is not already covered by a synonym. The draft is a proposed minor version (additions). If the proposal changes an existing term anyway, the report says so: publishing that change needs a major version and a full re-extraction. A person publishes the draft. Document text and questions are untrusted input, so in curated mode a term reaches the ontology only when someone publishes a version that contains it. Auto mode publishes the first discovered draft without that step.

Each published version renders the Turtle master into the forms the pipeline, the agent and the graph stores read. People edit the master. The renditions are produced from it.

A collection starts with an ontology one of two ways:

| | How | Then |
|---|---|---|
| Bring one | Set the collection's `ontology_dir` to a directory holding `ontology.ttl` (and optionally `shapes.ttl`); `terraform apply` uploads it | The sweep publishes and activates it and extracts against it. Discovery never runs. To change it, bump `owl:versionInfo` and apply |
| Discover one | Leave `ontology_dir` unset and upload documents | Discovery, then review, as described above. `ontology_mode = "curated"` (the default) stops at a draft for a person to change and publish; `"auto"` publishes the draft as 0.1.0 straight away |

1. Discover. With no ontology, the first run writes a draft as described in [How an ontology is derived](#how-an-ontology-is-derived).
2. Curate. The draft is Turtle (OWL plus generated SHACL) for a person to edit in git.
   `knowledge-store ontology pull <draft> ontology/` fetches it.
3. Release. `knowledge-store ontology publish ontology/ --activate` publishes the master as the
   version its `owl:versionInfo` names. Published versions are immutable. Each release renders
   the master into derived forms (see below).
4. Extract. Every document is extracted against the active version. The model must answer
   with a tool call whose schema is generated from the ontology. Every fact is checked for
   grounding (names and values must appear in the cited passages) and against SHACL, then
   repaired or dropped item by item.
5. Grow. Extraction records candidates, and a curator can keep a workbench report as an ontology
   request. `knowledge-store candidates --propose` drafts the next version from both, as described
   in [How an ontology is derived](#how-an-ontology-is-derived). A person curates and publishes it.

### Versions are classified, and the class decides the cost

| Change | Example | Bump | Applied by |
|---|---|---|---|
| descriptive | labels, synonyms, definitions | patch | nothing to re-extract |
| additive | a new class or property, a new subclass | minor | delta extraction of the new terms only |
| semantic | a changed parent, domain or range | major | full re-extraction |
| removal | a term removed | major | full re-extraction |

Publishing checks the version number against the change and refuses a bump that understates
it. Versions form a chain: an additive version's gold holds only its delta, and the graph for
a version is the union along the chain back to the last full version. That is what makes the
ontology cumulative.

Delta extraction selects documents where the new terms are likely to apply: their candidates
named the term, their text contains its label or a synonym, or they hold entities of a class
that just gained a subclass. That selection is a heuristic. A new term can apply to a document
it misses, so `knowledge-store extract --all-delta` runs the delta over everything, and a
periodic full re-extraction is worth budgeting.

### One master, many renditions

The curated Turtle is the master, and it is the only thing people edit. Each release renders
it into what each consumer needs, under `ontology/versions/<v>/renditions/`:

| Rendition | For |
|---|---|
| owl/ontology.ttl, owl/shapes.ttl | SPARQL stores (Neptune), SHACL validation, the pipeline |
| agent/ontology.md, agent/ontology.json | an agent's prompt or tools: compact types, relations, attributes and synonyms |
| neo4j/schema.cypher, neo4j/mapping.json, neo4j/schema.md | a property-graph projection: constraints, the class-to-label and property-to-relationship mapping, and the schema for Cypher agents |
| age/schema.sql | the same projection in PostgreSQL with Apache AGE |
| extraction/tool.json | the extraction tool's JSON Schema |
| jsonld/context.jsonld | JSON-LD over the same terms |

`knowledge-store ontology render ontology/ out/` shows what a release would ship.

On AWS it is a minimal GraphRAG reference architecture you deploy from Terraform: a pipeline
that applies the ontology and loads a knowledge graph into Amazon Neptune, a Bedrock Knowledge
Base over the passages, and a chat agent on AgentCore that queries the graph in the ontology's
terms and shows only answers it can ground in cited passages. See
[docs/architecture](docs/architecture/README.md).

## Deploy

The deployment code is in [`infra/`](infra): the module
[`infra/modules/knowledge-store`](infra/modules/knowledge-store), the root
[`infra/stack`](infra/stack), a CloudFormation launch stack, and a template for a deployment
repository of your own ([`examples/deployment`](examples/deployment)). Read
[QUICKSTART.md](QUICKSTART.md) to try it, and [docs/deploy/aws](docs/deploy/aws/README.md) to
install it in your own AWS estate. The pipeline image is built inside your account from this
repository's source.

## Install

```bash
pip install -e ".[aws]"     # from a clone
```

The core depends on no cloud's SDK. AWS and each optional backend is an extra, so an install
carries only what it uses:

| Extra | For |
|---|---|
| aws | S3 lakes (`s3://`), Amazon Bedrock, DynamoDB chat state |
| mongo, neo4j, age | the document store and graph backends |
| dev | all of the above, plus the test tools |

## Use

1. Upload documents to the lake's `landing/<collection>/` folder (the deployment's `upload_to`
   output). Any folder structure is kept as metadata. Supported now: .md, .txt, .csv, .html, .json
   and .pdf (with a text layer).
2. The upload starts the pipeline within a few minutes, and a schedule reruns it as a safety net.
3. Open the portal and sign in. Your cloud's guide says how the first user gets in. Ask a
   question: the answer lists its sources, and each statement links to its passage.
4. With `ontology_mode = "curated"` (the default), the first run stops after discovery with a
   draft. Curate and publish it:

   ```bash
   export LAKE_URI=s3://<lake bucket>
   # the draft id: list the lake's collections/<id>/ontology/drafts/
   knowledge-store ontology pull <draft id> ontology/
   # edit ontology/ontology.ttl, set owl:versionInfo "1.0.0", commit it
   knowledge-store ontology diff ontology/
   knowledge-store ontology publish ontology/ --activate
   ```

   Activating a version starts the pipeline, which extracts everything against it. With
   `ontology_mode = "auto"`, the first draft is published as 0.1.0 unreviewed, so uploads reach
   the portal unattended. Curate it later and publish a new version in its place.

## The workbench

Beside the chat is a workbench for the people who look after a collection:

- **Steps.** Every search, read and citation check the agent makes, shown as it happens, with the
  ontology terms each one touched. On a long question you can see whether it is searching the wrong
  type, reading the wrong documents or failing its checks.
- **What would it take?** For a question the chat could not answer, an analyst explores the same
  graph and reports what is missing: classes, relations and attributes to add, data to add, or facts
  extraction missed. A curator can keep the report as an ontology request, and requested terms join
  the candidate register that drafts the next ontology version.
- **Ontology use.** Which classes and properties questions ask for, read and cite, over all time,
  this month or this session, drawn as an overlay on the ontology page.

See [docs/workbench.md](docs/workbench.md), including what the usage numbers can and cannot tell
you.

## Sources and adapters

A source is an adapter type plus options, set in `sources` in terraform.tfvars:

| Type | Reads |
|---|---|
| s3_landing | a prefix in the lake (default `landing/`), or in another bucket you own |
| http_urls | a fixed list of HTTPS URLs. You are responsible for having the right to fetch and keep them. |
| local_dir | a local directory, for development |

An adapter only lists items (each with a version that changes when the item does) and fetches
bytes. Ingest does the rest: skipping what it has seen, content-addressing, and the manifest.
Parsing is chosen by format, separately, so adapters never parse. To add a source, implement
`items()` and `fetch()` (see `src/knowledge_store/adapters/base.py`) and register it in your
own package:

```toml
[project.entry-points."knowledge_store.adapters"]
sharepoint = "my_package.sharepoint:SharePointAdapter"
```

A source can be `scope = "private"`. Its facts are shown only to portal users who may read private
content: the `private-readers` Cognito group, or the private roles of `site_sign_in`.

A table is not this path yet. CSV and JSON in the lake are parsed as text and extracted like
prose, so a filter or a total has no cell to cite. The draft for keeping a mapped CSV as a table
beside the documents, and for how AWS Context Ontology Accelerator fits a later live source, is
[docs/architecture/aws/structured.md](docs/architecture/aws/structured.md). The worked catalog is the
invented tables in the space-missions corpus
([examples/space-missions](examples/space-missions/README.md)).

## Evaluate

Measure the agent against questions with known answers, including some the sources cannot
answer, which it must decline:

```bash
python -m knowledge_store.evals examples/evals/space-missions.yaml --lake <lake> --model <model id> --yes
```

The scoring needs no model as judge: facts stated, near misses avoided, the share of claims that
passed the citation checks, expected sources cited, and declines. See
[docs/architecture/aws/aws.md](docs/architecture/aws/aws.md#evaluation).

## Run it locally

```bash
pip install -e ".[dev]"     # or -e . with no extras: the core and its tests need no cloud
pytest
knowledge-store --lake ./build/lake ingest       # with config/sources.json pointing at local_dir
python -m knowledge_store.portal_api.local --lake ./build/lake
```

Model calls need `LLM_PROVIDER` and `EXTRACTION_MODEL_ID`. The provider is `anthropic` (with
`ANTHROPIC_API_KEY`, no extra needed) or `bedrock` (the aws extra and AWS credentials); see
`llm.py` for their settings.

## Costs

On AWS the knowledge graph (Neptune, about 60 USD a month) is the fixed cost; switch it off for
a small demo and the graph tools answer from memory. Everything else idles at close to nothing.
The deployment guide lists what it runs. Model calls are the cost that matters. Discovery reads `discovery.sample` x `discovery.resamples`
documents, whatever the collection's size. Extraction reads every document once per full
version. Chat is limited by `daily_questions` per user.

## Limits (read before relying on it)

- Entity resolution is naive. An entity's IRI is its root type plus its normalised name, so
  "NASA" and "National Aeronautics and Space Administration" are two nodes unless a document
  gives one as the other's alias.
- The portal's projection is held in memory by one function by default. That is right for tens of
  thousands of entities and wrong beyond it. For more, the pipeline can load the same projection
  into a document store and a graph database (`PROJECTION_STORE`, `GRAPH_BACKEND`; see
  [docs/architecture/aws/backends.md](docs/architecture/aws/backends.md)), behind
  the same API. On AWS the agent's graph tools query Neptune; the portal API's own routes still read memory.
- Delta selection is a heuristic (see above).
- Scanned PDFs need OCR, which is not built in.
- Extraction is synchronous (one model call per document). Batch inference (50% cheaper, for
  backfills) is the next step.
- Candidates and chat questions come from untrusted text. Nothing reaches the ontology without
  a person publishing it.

## Licence

Apache License 2.0: see [LICENSE](LICENSE) and [NOTICE](NOTICE). Third-party components and their licences are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Contributions are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
