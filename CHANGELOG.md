# Changelog

Notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [semantic versioning](https://semver.org/).

From 0.2.0 on, releases are made by Release Please from the pull requests merged to `main`: a pull request's title is its line here, and the release pull request adds the next section, bumps the version and, when merged, tags `vX.Y.Z` and publishes the GitHub Release. The rules are in [CONTRIBUTING.md](CONTRIBUTING.md#releases). Do not add lines here by hand.

## [0.7.1](https://github.com/patternode/knowledge-store/compare/v0.7.0...v0.7.1) (2026-10-24)


### Fixed

* **ontology:** let a domain property keep a name the measures ontology also uses ([#115](https://github.com/patternode/knowledge-store/issues/115)) ([5feb032](https://github.com/patternode/knowledge-store/commit/5feb032c5423fd8fffc9fc29975834e0cf438f9d))

## [0.7.0](https://github.com/patternode/knowledge-store/compare/v0.6.0...v0.7.0) (2026-10-24)


### Added

* **ontology:** conform literals before chunking, and add the value kinds and measures ontologies ([#111](https://github.com/patternode/knowledge-store/issues/111)) ([f1e1bd9](https://github.com/patternode/knowledge-store/commit/f1e1bd9fa8367f0e513d1f55ac3b3ca64e9cae17))

## [0.6.0](https://github.com/patternode/knowledge-store/compare/v0.5.0...v0.6.0) (2026-10-24)


### ⚠ BREAKING CHANGES

* **evaluation:** DeepEval as the evaluation framework, a runner and a model grader beside the deterministic score ([#110](https://github.com/patternode/knowledge-store/issues/110))

### Added

* **evaluation:** DeepEval as the evaluation framework, a runner and a model grader beside the deterministic score ([#110](https://github.com/patternode/knowledge-store/issues/110)) ([e62d472](https://github.com/patternode/knowledge-store/commit/e62d47235dffbc51e2af712e0a809f8df7522ca9))
* **evaluation:** grade another system's answers with DeepEval, and judge completeness ([#113](https://github.com/patternode/knowledge-store/issues/113)) ([5b9fa9d](https://github.com/patternode/knowledge-store/commit/5b9fa9d4960c22ea72b1e321b458b703835cf43b))
* **examples:** an EnterpriseRAG-Bench slice and its 490 questions as a testbed for graph extraction ([#109](https://github.com/patternode/knowledge-store/issues/109)) ([7e17ed1](https://github.com/patternode/knowledge-store/commit/7e17ed1d974e15c63b9a06b4a5e6a67c16e0ad56))

## [0.5.0](https://github.com/patternode/knowledge-store/compare/v0.4.1...v0.5.0) (2026-10-20)


### ⚠ BREAKING CHANGES

* bounded contexts with slices and ports, an Evaluation context, and tests at every level ([#108](https://github.com/patternode/knowledge-store/issues/108))

### Added

* bounded contexts with slices and ports, an Evaluation context, and tests at every level ([#108](https://github.com/patternode/knowledge-store/issues/108)) ([d65f229](https://github.com/patternode/knowledge-store/commit/d65f229f96dc38f60cc8781a9297883ce4f70fe5))


### Documentation

* **architecture:** a target-state view by subdomain, generated from the pages, with the investigation behind it ([#103](https://github.com/patternode/knowledge-store/issues/103)) ([5727d30](https://github.com/patternode/knowledge-store/commit/5727d305261a0fe27579c9bbc8687aa3f9a3f25d))
* **architecture:** show the context map first on the contexts page ([#104](https://github.com/patternode/knowledge-store/issues/104)) ([0eef0e8](https://github.com/patternode/knowledge-store/commit/0eef0e8de664e2489b3cfb56f7e0f7422eaca1c5))

## [0.4.1](https://github.com/patternode/knowledge-store/compare/v0.4.0...v0.4.1) (2026-10-18)


### Documentation

* **architecture:** diagrams for the landscape, use cases and contexts, cards for the building blocks, and the reference architecture on RA-001 ([#98](https://github.com/patternode/knowledge-store/issues/98)) ([cdcf883](https://github.com/patternode/knowledge-store/commit/cdcf8830e24f17a68c202cd5d9434a56fddd548d))
* make Knowledge Store agnostic of any consuming deployment ([#101](https://github.com/patternode/knowledge-store/issues/101)) ([097658e](https://github.com/patternode/knowledge-store/commit/097658e1cac386b58aebe74edfa75249aa927357))

## [0.4.0](https://github.com/patternode/knowledge-store/compare/v0.3.0...v0.4.0) (2026-10-17)


### Added

* **site:** the architecture laid out by space, design notes in docs/design, and a page banner linking each deck's slides and PDF ([#95](https://github.com/patternode/knowledge-store/issues/95)) ([6773a9b](https://github.com/patternode/knowledge-store/commit/6773a9b75dbce557fdcf2cc4009f9b3e086ccbae))


### Fixed

* **launch:** the launch stack defaults to the v0.3.0 source archive, and each release moves it ([#87](https://github.com/patternode/knowledge-store/issues/87)) ([d33bf2f](https://github.com/patternode/knowledge-store/commit/d33bf2f2f43903e8296d42752b64b97418c384f9))
* **site:** list each register page once in the sidebar, and put RA-001's diagram on a slide ([#96](https://github.com/patternode/knowledge-store/issues/96)) ([8e1ea9f](https://github.com/patternode/knowledge-store/commit/8e1ea9f7c98994396e9245e450f23bed7d7a9af0))


### Documentation

* **architecture:** building blocks at container grain, and the AP and RA series for the two kinds of pattern document ([#92](https://github.com/patternode/knowledge-store/issues/92)) ([9e89691](https://github.com/patternode/knowledge-store/commit/9e8969121d4af681b54324ff289a0ee804ec100d))
* **architecture:** compliant with the continuum, checked in CI, skills pinned to releases ([#93](https://github.com/patternode/knowledge-store/issues/93)) ([e7acf30](https://github.com/patternode/knowledge-store/commit/e7acf301553f4947eff0203893e48a8a48dfa359))
* **architecture:** draw the domain and its subdomains ([#97](https://github.com/patternode/knowledge-store/issues/97)) ([aa72631](https://github.com/patternode/knowledge-store/commit/aa72631efae6be4d454f02ca21729add217c6fd3))
* **architecture:** the architecture of Knowledge Store, expressed with the continuum ([#90](https://github.com/patternode/knowledge-store/issues/90)) ([7465392](https://github.com/patternode/knowledge-store/commit/7465392308156b5af8bc82f198a0788f8b656956))
* **site:** publish the documentation with Docusaurus on GitHub Pages ([#88](https://github.com/patternode/knowledge-store/issues/88)) ([ad92779](https://github.com/patternode/knowledge-store/commit/ad9277926a47d09074de021adc048c6d5027e98d))

## [0.3.0](https://github.com/patternode/knowledge-store/compare/v0.2.0...v0.3.0) (2026-10-16)


### Added

* **portal:** a branding input (logo, icon, colours, stylesheet, files), with the security design and the source-controls design ([#85](https://github.com/patternode/knowledge-store/issues/85)) ([7846ee7](https://github.com/patternode/knowledge-store/commit/7846ee7dd41d2450a4941d6bead3a9e8b8138b40))

## [0.2.0] - 2026-10-16

Cut by hand from everything merged since 0.1.2, before Release Please took over. AWS is the one supported deployment. The Azure and Google Cloud deployments built and withdrawn between 0.1.2 and 0.2.0 were never released, and the graph and document backends they brought stay, in `docs/design/aws/backends.md`.

### Added

- The chat agent behind the portal: answers are claims with verbatim quotes, every citation is checked against the passage the caller can read, failures get one repair turn, and only checked claims are shown, with links to their passages and documents. It declines when the sources cannot answer.
- Valves: a Bedrock Guardrail on questions and on the grounding of claims, tool and model call limits per question, the chat API's reserved concurrency, and an optional monthly budget.
- An evaluation framework (`python -m knowledge_store.evals`) with deterministic scoring, an evaluation set for the space-missions example, and one for the Sherlock Holmes stories (`examples/evals/sherlock-holmes.yaml`, collection `holmes`): ten questions across lookup, list, multi-hop, comparison and unanswerable, including where Moriarty appears (The Final Problem, Reichenbach as a whole word) and where he was born, which the stories never say. Each answer was checked against the fetched text.
- A minimal chat page (`chat/`), which replaces the explorer as the AWS portal, and an ontology page beside it (`chat/ontology.html`): the active ontology as a force-directed graph, with core classes, population arcs, declared relations and the relations seen in the data but not declared, and its statistics. The projection's ontology index gains `observed`, the class-to-class counts behind it.
- The workbench beside the chat ([docs/workbench.md](docs/workbench.md)). It shows the agent's steps as they happen (the agent streams them, and the portal keeps them with the pending answer). "What would it take?" runs an analyst that reports the ontology extensions, data and missed extraction a question needs, and curators can keep its report as an ontology request, which the candidate register reads (`asked`). The ontology terms each answer asked for, read and cited are counted per collection (all time and per month), with a question overlay on the ontology page. The workbench groups steps, cost, ontology terms and this session, and each section starts collapsed.
- A citation opens with the quoted words highlighted in the passage. A citation of a mapped table shows that row, with the cited cell highlighted.
- Structured lookup, per collection. A collection turns it on by placing `mappings.yaml` (and, optionally, `metrics.osi.yaml`) next to its ontology. A collection without those files is unchanged. Publish checks the mapping and writes an R2RML rendition. The sweep binds each mapped CSV, TSV or JSON array as a snapshot and skips it in refine and extract, so an unmapped CSV stays prose. `describe_structured`, `lookup_rows` and `aggregate` read that snapshot, and a cell or a metric citation is checked against it. Core vocabulary 1.1.0 adds `ks:Cell` and `ks:recordedIn`. A live Context Ontology Accelerator source is not wired up.
- On AWS, a minimal GraphRAG reference architecture: the sweep loads the gold RDF into Amazon Neptune (one named graph per document, and the ontology), and the agent's graph tools query it with fixed SPARQL built from the ontology (`knowledge_graph`, on by default).
- A Bedrock Knowledge Base on S3 Vectors over every passage, one vector per passage, for search by meaning (`knowledge_base`, on by default).
- Bring your own ontology: a collection's `ontology_dir` is published and activated in place of discovery, and changed by bumping its version.
- A review pass after discovery that adds hierarchy, merges near-duplicates and fixes domains, ranges and datatypes, recorded edit by edit in the draft's report (`discovery.review`, on by default).
- Publish refuses an `owl:versionIRI` that does not name the version, and accepts a change to the ontology's own label or comment as a patch.
- AWS inputs for deploying into an existing estate, each optional with today's behaviour as its default: `network` (the VPC's CIDR and zones, a NAT gateway, or a VPC and subnets you bring), `portal_domain` (the portal on your own domain with an ACM certificate), `permissions_boundary` (on every IAM role) and `log_retention_days`. A `portal_cloudfront_domain` output.
- `portal_web_acl_arn` attaches an existing web ACL, such as a CloudFront flat-rate plan's, to the portal's distribution, and `api_throttle` sets the portal API's throttle (default 20 a second, burst 50, as before). Both are off or unchanged by default.
- Sign-in through a host website (`site_sign_in`): a website that signs people in frames the portal and hands each person's page a short ES256 grant for the lab, which the portal API verifies on every request (`knowledge_store.site_grant`) in place of Cognito. Roles decide who may read and who may read private sources. The portal asks the agent as a public or a private service client, and CloudFront lets the website frame the pages. Off by default.
- Optional graph and document backends (Neo4j, PostgreSQL with Apache AGE, MongoDB) filled by a `load` stage, the `age` rendition, a MongoDB chat state, and configurable claim names.
- An AWS installation pack (`docs/deploy/aws/`): a step-by-step guide, every parameter with a worksheet, the components and how the Terraform expresses them, and the reference architecture diagram, also as an editable draw.io file (`docs/deploy/aws/architecture.drawio`) beside the SVG and PNG, which show sign-in through a host website and the ontology page.

### Changed

- AWS: the agent module is the chat agent and its tools only. Memory, Code Interpreter, Browser, Evaluations, Registry, Harness, the Cedar policy engine and the agent's own client-credentials identity are removed; the interceptor still scopes every tool call to the caller. The `agent` variable is now `{ runtime, prod_version, model_id }`, and the launch stack's agent parameters are replaced by EnableKnowledgeGraph, EnableKnowledgeBase and EnableAgentRuntime.
- The tools are split into a graph toolset and a passages toolset, one Lambda each (`TOOLSET`), with a schema each (`tools/schema-graph.json`, `tools/schema-passages.json`).
- `examples/agent` (the task agent's client) is removed; `python -m knowledge_store.evals --api` calls the deployed chat.
- Neptune's default instance class is `db.t3.medium` (was `db.t4g.medium`), after a deploy in us-east-1 found no `t4g.medium` capacity in four zones. An existing cluster's instance changes in place, with a restart, unless `knowledge_graph.instance_class` is set.
- The evaluation report names its two mistake counts: "False negatives: abstained on an answerable question" and "False positives: answered an unanswerable question". The `score.py` docstring and the evaluation section of the AWS architecture define true and false positives and negatives. The keys in `results.json` (`false_abstentions`, `missed_abstentions`) are unchanged.
- The valves include the catalog questions a mapped table answers: Juno's sample cost, the Atlas V missions, that count, their total sample cost, and the name of `atlas-v-551`. When the collection's mapping has the attribute or the metric, those questions are added to the agent's prompt and to the portal's prompt. A claim from one of them is checked against the cell or the figure. The tool-budget message and the guardrail say the same.
- boto3 is now the `aws` extra instead of a core dependency. Install with `pip install ".[aws]"` to use S3 lakes, Bedrock or DynamoDB. The pipeline image installs it by default.
- The README describes the core and links the AWS guide.
- `THIRD_PARTY_NOTICES.md` lists the optional extras' dependencies and their licences.

### Fixed

- A cited total is checked against its own computation. An ad hoc figure's id names its type, attribute, filters and group-by (`m:<op>:<digest>/<snapshot>`), so two totals over one snapshot no longer share an id, a wrong total can no longer pass on another citation's figure, and a true one is no longer dropped for sharing an id.
- One group of a grouped figure can be cited (`group_by`, `group`); before, every grouped answer was dropped.
- Table values written as `1,100`, `$1,200` or `14 July 2023` are stored and compared in one canonical form, so totals, filters, date ranges and citations read them; a value that is not its type is skipped and counted, never summed.
- A column mapped in a later version, or a table whose scope changes, is bound again instead of being kept unchanged with no cells.
- `describe_structured` no longer shows a private table, or a metric over one, to a public caller.
- Keys containing commas stay distinct rows; key columns can be filtered; a row with only its key is counted; a file that names a column twice, is not UTF-8 or is too large is reported instead of bound wrongly.
- The portal's own tool loop returns a failed tool call to the model instead of failing the answer, and shows a cited figure only when a tool returned it.
- The grounding guardrail sees a cited cell's whole row and a figure's computation, not just `column: value`.
- The question cost keeps model calls the hooks did not report.
- The chat page: switching collection closes the old collection's sources; a focused workbench section keeps focus while a question runs; citation links' expanded state stays in step with the source panel; highlights stay aligned after characters such as `İ`; a closed workbench stays closed; a sample link to a mapped table (`tables/<name>.csv`) opens its bound snapshot (`GET /api/table`).
- The chat page stalled after every sign-in: its own `history()` function hid `window.history`, so stripping the sign-in code from the URL threw. Renamed. The page's files are now served with `Cache-Control: no-cache`, so a browser never runs a previous release's `app.js` against a new page.
- The passage tools could not read the collection's `ontology/active.json`, which the index loads first, so every passage search failed with an S3 403. Their role now reads the ontology layer, as the graph tools' does.
- A mapped CSV is found when it is uploaded into the collection's landing folder, not only when its key ends with the mapping's `tables/` path. The same bytes uploaded again under the mapped path stay visible. Two files of that name are reported rather than one being chosen. A `mappings.yaml` added beside an already published ontology version is reported instead of ignored, and the sweep publishes that ontology before it parses uploads.
- The space-missions evaluation set asks the catalog as well as the documents: Juno's sample cost, the Atlas V missions, that count, their total sample cost, and the name of `atlas-v-551`. An offline smoke test answers those from the bound tables.
- Fixes from a full security review and scan (#76): private-only names, types and summary fields kept from public callers, the agent's own daily limit, CloudFront's origin header required by the API, internal redirects and oversized inputs refused at ingest, and narrower IAM.

### Documentation

- `docs/design/aws/structured.md` explains how to add tables to a collection whose ontology came from discovery (the attributes to add, a mapping in that ontology's terms, `ontology_dir` and the CSV upload) and the symptom when the mapping is missing.
- [Scalability](docs/design/aws/scalability.md): what limits each part of the stack as a collection grows, what an organisation's curated data needs, and Neptune compared with Neo4j as the graph, with the managed services' limits and sources.

## [0.1.2] - 2026-10-03

### Fixed

- Discovery tolerates tool input sent as JSON strings (#6).

## [0.1.1] - 2026-09-30

### Fixed

- First image builds wait for the build trigger's permissions (#4).
- Image builds tag from the source bundle's name (#5).

## [0.1.0] - 2026-09-29

### Added

- Source adapters (S3 landing, HTTPS URLs, local directory) and an entry-point registry.
- A layered, content-addressed lake: landing, bronze, silver, and gold per ontology version.
- Ontology discovery (resampled, with a stability score), curated immutable releases with change classification and semver checks, candidate capture, revision drafts and delta extraction over a version chain.
- Release renditions: OWL and SHACL, an agent vocabulary, a Neo4j schema and mapping, the extraction tool schema and a JSON-LD context.
- Collections: several corpora in one stack, one ontology each.
- A portal (CloudFront, Cognito, an HTTP API and Lambda) and a local preview server.
- A Terraform stack whose only required input is the admin email, and a CloudFormation launch stack that runs it from the AWS console.
- AgentCore Gateway tools and an example task agent.
- Sample corpora: an original space-missions set (CC0) and a fetch script for the public-domain Sherlock Holmes stories.
- A reusable Terraform module (`infra/modules/knowledge-store`) and a template for a deployment repository of your own (`examples/deployment`).
