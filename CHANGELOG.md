# Changelog

Notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [semantic versioning](https://semver.org/).

## [Unreleased]

### Removed

- The Azure deployment (`deploy/azure/`) and its code: the Blob Storage lake, the `foundry` model provider, Entra ID sign-in for AGE, the Azure host, token verification (`authn.py`) and the MCP server it served (`tools/mcp.py`). The `azure` extra is gone.
- Google Cloud: the Cloud Storage lake, the `vertex` model provider, the Spanner Graph rendition and the `gcp` extra.
- The reference architectures for Azure and Google Cloud. AWS is the one supported deployment; the graph and document backends stay, in `docs/architectures/backends.md`.

### Added since 0.1.2

- A citation opens with the quoted words highlighted in the passage. A citation of a mapped table shows that row, with the cited cell highlighted.
- Structured lookup, per collection. A collection turns it on by placing `mappings.yaml` (and, optionally, `metrics.osi.yaml`) next to its ontology. A collection without those files is unchanged. Publish checks the mapping and writes an R2RML rendition. The sweep binds each mapped CSV, TSV or JSON array as a snapshot and skips it in refine and extract, so an unmapped CSV stays prose. `describe_structured`, `lookup_rows` and `aggregate` read that snapshot, and a cell or a metric citation is checked against it. Core vocabulary 1.1.0 adds `ks:Cell` and `ks:recordedIn`. A live Context Ontology Accelerator source is not wired up.
- The workbench beside the chat ([docs/workbench.md](docs/workbench.md)). It shows the agent's steps as they happen (the agent streams them, and the portal keeps them with the pending answer). "What would it take?" runs an analyst that reports the ontology extensions, data and missed extraction a question needs, and curators can keep its report as an ontology request, which the candidate register reads (`asked`). The ontology terms each answer asked for, read and cited are counted per collection (all time and per month), with a question overlay on the ontology page.
- On AWS, a minimal GraphRAG reference architecture: the sweep loads the gold RDF into Amazon Neptune (one named graph per document, and the ontology), and the agent's graph tools query it with fixed SPARQL built from the ontology (`knowledge_graph`, on by default).
- A Bedrock Knowledge Base on S3 Vectors over every passage, one vector per passage, for search by meaning (`knowledge_base`, on by default).
- The agent is now a chat agent behind the portal: answers are claims with verbatim quotes, every citation is checked against the passage the caller can read, failures get one repair turn, and only checked claims are shown, with links to their passages and documents. It declines when the sources cannot answer.
- Valves: a Bedrock Guardrail on questions and on the grounding of claims, tool and model call limits per question, the chat API's reserved concurrency, and an optional monthly budget.
- An evaluation framework (`python -m knowledge_store.evals`) with deterministic scoring, and an evaluation set for the space-missions example.
- A minimal chat page (`chat/`), which replaces the explorer as the AWS portal.
- An ontology page beside the chat (`chat/ontology.html`): the active ontology as a force-directed graph, with core classes, population arcs, declared relations and the relations seen in the data but not declared, and its statistics. The projection's ontology index gains `observed`, the class-to-class counts behind it.

- Bring your own ontology: a collection's `ontology_dir` is published and activated in place of discovery, and changed by bumping its version.
- A review pass after discovery that adds hierarchy, merges near-duplicates and fixes domains, ranges and datatypes, recorded edit by edit in the draft's report (`discovery.review`, on by default).
- Publish refuses an `owl:versionIRI` that does not name the version, and accepts a change to the ontology's own label or comment as a patch.
- AWS inputs for deploying into an existing estate, each optional with today's behaviour as its default: `network` (the VPC's CIDR and zones, a NAT gateway, or a VPC and subnets you bring), `portal_domain` (the portal on your own domain with an ACM certificate), `permissions_boundary` (on every IAM role) and `log_retention_days`. A `portal_cloudfront_domain` output.
- The AWS reference architecture as an editable draw.io file (`docs/deploy/aws/architecture.drawio`), beside the SVG and PNG, which now show sign-in through a host website and the ontology page.
- Sign-in through a host website (`site_sign_in`): a website that signs people in frames the portal and hands each person's page a short ES256 grant for the lab, which the portal API verifies on every request (`knowledge_store.site_grant`) in place of Cognito. Roles decide who may read and who may read private sources. The portal asks the agent as a public or a private service client, and CloudFront lets the website frame the pages. Off by default.
- The passage tools could not read the collection's `ontology/active.json`, which the index loads first, so every passage search failed with an S3 403. Their role now reads the ontology layer, as the graph tools' does.
- The chat page stalled after every sign-in: its own `history()` function hid `window.history`, so stripping the sign-in code from the URL threw. Renamed. The page's files are now served with `Cache-Control: no-cache`, so a browser never runs a previous release's `app.js` against a new page.
- Neptune's default instance class is `db.t3.medium` (was `db.t4g.medium`), after a deploy in us-east-1 found no `t4g.medium` capacity in four zones. An existing cluster's instance changes in place, with a restart, unless `knowledge_graph.instance_class` is set.
- An AWS installation pack (`docs/deploy/aws/`): a step-by-step guide, every parameter with a worksheet, the components and how the Terraform expresses them, and the reference architecture diagram.

### Added

- An Azure deployment (`deploy/azure/`): Blob Storage lake, Claude in Microsoft Foundry, Entra ID sign-in, a Function App for the portal API, chat and MCP tools, and API Management in front of MCP.
- Cloud ports: `BlobStore` and `GcsStore` lakes, the `foundry` and `vertex` model providers, a MongoDB chat state, and configurable claim names.
- Optional graph and document backends (Neo4j, PostgreSQL with Apache AGE, MongoDB) filled by a `load` stage, and `age` and `spanner` renditions.
- Reference architectures for Azure and Google Cloud (`docs/architectures/`).

### Changed

- AWS: the agent module is the chat agent and its tools only. Memory, Code Interpreter, Browser, Evaluations, Registry, Harness, the Cedar policy engine and the agent's own client-credentials identity are removed; the interceptor still scopes every tool call to the caller. The `agent` variable is now `{ runtime, prod_version, model_id }`, and the launch stack's agent parameters are replaced by EnableKnowledgeGraph, EnableKnowledgeBase and EnableAgentRuntime.
- The tools are split into a graph toolset and a passages toolset, one Lambda each (`TOOLSET`), with a schema each (`tools/schema-graph.json`, `tools/schema-passages.json`).
- `examples/agent` (the task agent's client) is removed; `python -m knowledge_store.evals --api` calls the deployed chat.

- Azure's deployment code moved from `infra/azure/` and `functions/azure/` to `deploy/azure/`. AWS stays in `infra/`, so pinned AWS module paths do not change.
- boto3 is now the `aws` extra instead of a core dependency. Install with `pip install ".[aws]"` to use S3 lakes, Bedrock or DynamoDB. The pipeline image installs it by default.
- The README describes the core and links a guide per cloud.
- `THIRD_PARTY_NOTICES.md` lists the optional extras' dependencies and their licences.

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
