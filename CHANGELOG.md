# Changelog

Notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [semantic versioning](https://semver.org/).

## [Unreleased]

### Added

- An Azure deployment (`deploy/azure/`): Blob Storage lake, Claude in Microsoft Foundry, Entra ID sign-in, a Function App for the portal API, chat and MCP tools, and API Management in front of MCP.
- Cloud ports: `BlobStore` and `GcsStore` lakes, the `foundry` and `vertex` model providers, a MongoDB chat state, and configurable claim names.
- Optional graph and document backends (Neo4j, PostgreSQL with Apache AGE, MongoDB) filled by a `load` stage, and `age` and `spanner` renditions.
- Reference architectures for Azure and Google Cloud (`docs/architectures/`).

### Changed

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
