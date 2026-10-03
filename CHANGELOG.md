# Changelog

Notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [semantic versioning](https://semver.org/).

## [Unreleased]

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

### Changed

- Azure's deployment code moved from `infra/azure/` and `functions/azure/` to `deploy/azure/`. AWS stays in `infra/`, so pinned AWS module paths do not change.
- boto3 is now the `aws` extra instead of a core dependency. Install with `pip install ".[aws]"` to use S3 lakes, Bedrock or DynamoDB. The pipeline image installs it by default.
- The README describes the core and links a guide per cloud.
