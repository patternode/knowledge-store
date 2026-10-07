# Changelog

Notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [semantic versioning](https://semver.org/).

## [Unreleased]

### Added since 0.1.2

- On AWS, a minimal GraphRAG reference architecture: the sweep loads the gold RDF into Amazon Neptune (one named graph per document, and the ontology), and the agent's graph tools query it with fixed SPARQL built from the ontology (`knowledge_graph`, on by default).
- A Bedrock Knowledge Base on S3 Vectors over every passage, one vector per passage, for search by meaning (`knowledge_base`, on by default).
- The agent is now a chat agent behind the portal: answers are claims with verbatim quotes, every citation is checked against the passage the caller can read, failures get one repair turn, and only checked claims are shown, with links to their passages and documents. It declines when the sources cannot answer.
- Valves: a Bedrock Guardrail on questions and on the grounding of claims, tool and model call limits per question, the chat API's reserved concurrency, and an optional monthly budget.
- An evaluation framework (`python -m knowledge_store.evals`) with deterministic scoring, and an evaluation set for the space-missions example.
- A minimal chat page (`chat/`), which replaces the explorer as the AWS portal.

- Bring your own ontology: a collection's `ontology_dir` is published and activated in place of discovery, and changed by bumping its version.
- A review pass after discovery that adds hierarchy, merges near-duplicates and fixes domains, ranges and datatypes, recorded edit by edit in the draft's report (`discovery.review`, on by default).
- Publish refuses an `owl:versionIRI` that does not name the version, and accepts a change to the ontology's own label or comment as a patch.

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
