# Knowledge Store

Put documents in a data lake and get an ontology-typed knowledge graph, and a portal to browse
its concepts and ask questions about them, for any domain. The ontology is discovered from the
documents first. After that, it is maintained under version control, released in controlled
versions, and grown from the terms extraction finds it lacks.

It runs on AWS or Azure, in one account or subscription from one Terraform stack, or on your own
machine over a local folder. Model calls go to Claude through your cloud's own service (Amazon
Bedrock, or Microsoft Foundry), so no data leaves your cloud, or to the Anthropic API.

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

A collection starts with an ontology one of two ways:

| | How | Then |
|---|---|---|
| Bring one | Set the collection's `ontology_dir` to a directory holding `ontology.ttl` (and optionally `shapes.ttl`); `terraform apply` uploads it | The sweep publishes and activates it and extracts against it. Discovery never runs. To change it, bump `owl:versionInfo` and apply |
| Discover one | Leave `ontology_dir` unset and upload documents | Discovery, then review, as below. `ontology_mode = "curated"` (the default) stops at a draft for a person to change and publish; `"auto"` publishes the draft as 0.1.0 straight away |

1. Discover. With no ontology, the first run samples the collection and proposes one:
   open proposals per document, aggregation, then consolidation into a small ontology with
   definitions, synonyms, a hierarchy, and domains and ranges. The method follows EDC
   (extract, define, canonicalise). Discovery repeats on several samples and reports how
   stable each type is, because LLM ontology induction varies from run to run and nothing
   in the literature measures by how much. Then a review pass (`discovery.review`, on by
   default) sees the draft with each term's document support and returns edits: parents
   where one class is a kind of another, merges of near-duplicates, drops of noise, and
   fixes to domains, ranges and datatypes. They are applied deterministically, each with its
   reason in the draft's report, so a curator can see and undo every one.
2. Curate. The draft is Turtle (OWL plus generated SHACL) for a person to edit in git.
   `knowledge-store ontology pull <draft> ontology/` fetches it.
3. Release. `knowledge-store ontology publish ontology/ --activate` publishes the master as the
   version its `owl:versionInfo` names. Published versions are immutable. Each release renders
   the master into derived forms (see below).
4. Extract. Every document is extracted against the active version. The model must answer
   with a tool call whose schema is generated from the ontology. Every fact is checked for
   grounding (names and values must appear in the cited passages) and against SHACL, then
   repaired or dropped item by item.
5. Grow. Extraction also records candidates, the things the ontology has no term for, with
   verbatim evidence. They never enter the graph. `knowledge-store candidates --propose`
   aggregates them and drafts the next version for a person to curate.

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
| age/schema.sql, spanner/schema.sql | the same projection in PostgreSQL with Apache AGE, and in Spanner Graph |
| extraction/tool.json | the extraction tool's JSON Schema |
| jsonld/context.jsonld | JSON-LD over the same terms |

`knowledge-store ontology render ontology/ out/` shows what a release would ship.

## Deploy

The core (the pipeline, the ontology lifecycle, the portal and its API, and the knowledge tools)
is the same everywhere. Each cloud adds its storage, model provider, sign-in and hosting, and its
own Terraform:

| Cloud | State | Deployment code | Start here |
|---|---|---|---|
| AWS | Built: the reference implementation | [`infra/`](infra): the module [`infra/modules/knowledge-store`](infra/modules/knowledge-store), the root [`infra/stack`](infra/stack), a CloudFormation launch stack, and a template for a deployment repository of your own ([`examples/deployment`](examples/deployment)) | [QUICKSTART.md](QUICKSTART.md) |
| Azure | Built | [`deploy/azure/`](deploy/azure): the module, the root, the state bootstrap and the Function App | [docs/architectures/azure-setup.md](docs/architectures/azure-setup.md) |
| Google Cloud | Designed. Storage and the Vertex AI provider are built; there is no deployment yet | none yet | [docs/architectures/gcp.md](docs/architectures/gcp.md) |

How the clouds map onto one design is in [docs/architectures](docs/architectures/README.md).
On every cloud the pipeline image is built inside your account from this repository's source.

## Install

```bash
pip install -e ".[aws]"     # from a clone; or [azure], or [gcp]
```

The core depends on no cloud's SDK. Each cloud and each optional backend is an extra, so an install
carries only what it uses:

| Extra | For |
|---|---|
| aws | S3 lakes (`s3://`), Amazon Bedrock, DynamoDB chat state |
| azure | Blob Storage lakes (`az://`), Claude in Microsoft Foundry with Entra ID, the Azure host |
| gcp | Cloud Storage lakes (`gs://`), Claude on Vertex AI |
| mongo, neo4j, age | the document store and graph backends |
| dev | all of the above, plus the test tools |

## Use

1. Upload documents to the lake's `landing/<collection>/` folder (the deployment's `upload_to`
   output). Any folder structure is kept as metadata. Supported now: .md, .txt, .csv, .html, .json
   and .pdf (with a text layer).
2. The upload starts the pipeline within a few minutes, and a schedule reruns it as a safety net.
3. Open the portal and sign in. Your cloud's guide says how the first user gets in.
4. With `ontology_mode = "curated"` (the default), the first run stops after discovery with a
   draft. Curate and publish it:

   ```bash
   export LAKE_URI=s3://<lake bucket>                     # or az://<account>/<container>
   knowledge-store ontology pull <draft id> ontology/    # the draft id is on the portal's Overview
   # edit ontology/ontology.ttl, set owl:versionInfo "1.0.0", commit it
   knowledge-store ontology diff ontology/
   knowledge-store ontology publish ontology/ --activate
   ```

   Activating a version starts the pipeline, which extracts everything against it. With
   `ontology_mode = "auto"`, the first draft is published as 0.1.0 unreviewed, so uploads reach
   the portal unattended. Curate it later and publish a new version in its place.

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
content: the `private-readers` Cognito group on AWS, the `private-reader` app role on Azure.

## Run it locally

```bash
pip install -e ".[dev]"     # or -e . with no extras: the core and its tests need no cloud
pytest
knowledge-store --lake ./build/lake ingest       # with config/sources.json pointing at local_dir
python -m knowledge_store.portal_api.local --lake ./build/lake
```

Model calls need `LLM_PROVIDER` and `EXTRACTION_MODEL_ID`. The provider is `anthropic` (with
`ANTHROPIC_API_KEY`, no extra needed), `bedrock` (the aws extra and AWS credentials), `foundry`
(Claude in Microsoft Foundry, the azure extra) or `vertex` (Claude on Vertex AI, the gcp extra);
see `llm.py` for their settings.

## Costs

Each stack idles at close to nothing: no always-on compute and no database server unless you turn
on a graph or document backend. Each cloud's guide lists what it runs. Model calls are the cost
that matters. Discovery reads `discovery.sample` x `discovery.resamples`
documents, whatever the collection's size. Extraction reads every document once per full
version. Chat is limited by `daily_questions` per user.

## Limits (read before relying on it)

- Entity resolution is naive. An entity's IRI is its root type plus its normalised name, so
  "NASA" and "National Aeronautics and Space Administration" are two nodes unless a document
  gives one as the other's alias.
- The portal's projection is held in memory by one function by default. That is right for tens of
  thousands of entities and wrong beyond it. For more, the pipeline can load the same projection
  into a document store and a graph database (`PROJECTION_STORE`, `GRAPH_BACKEND`; see
  [docs/architectures](docs/architectures/README.md#new-the-graph-and-document-backends)), behind
  the same API. The AWS stack does not deploy either yet.
- Delta selection is a heuristic (see above).
- Scanned PDFs need OCR, which is not built in.
- Extraction is synchronous (one model call per document). Batch inference (50% cheaper, for
  backfills) is the next step.
- Candidates and chat questions come from untrusted text. Nothing reaches the ontology without
  a person publishing it.

## Licence

Apache License 2.0: see [LICENSE](LICENSE) and [NOTICE](NOTICE). Third-party components and their licences are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Contributions are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
