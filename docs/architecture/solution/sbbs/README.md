# Solution building blocks

The technologies chosen to realise each architecture building block: what was built or bought, and why. Twelve, as deployed at 0.3.0 and recalibrated to container grain on 2026-10-17: each is one C4 container with its products chosen, the same container as the ABB it realises, per the [building block calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md). The register is [../sbbs.csv](../sbbs.csv).

| SBB | Realises | Products |
|---|---|---|
| [SBB-001 Lake on S3](SBB-001-lake-on-s3/index.md) | ABB-002 | Amazon S3 |
| [SBB-002 Sweep on ECS Fargate: the pipeline image with its triggers](SBB-002-sweep-on-ecs-fargate-the-pipeline-image-with-its-triggers/index.md) | ABB-004 | Amazon ECS on AWS Fargate; Amazon EventBridge, EventBridge Pipes and Scheduler; Amazon SQS; rdflib; pySHACL; pypdf; PyYAML; boto3; Claude through the model client |
| [SBB-003 Knowledge graph on Amazon Neptune](SBB-003-knowledge-graph-on-amazon-neptune/index.md) | ABB-011 | Amazon Neptune Database |
| [SBB-004 Passage index on Bedrock Knowledge Base with S3 Vectors](SBB-004-passage-index-on-bedrock-knowledge-base-with-s3-vectors/index.md) | ABB-013 | Amazon Bedrock Knowledge Bases; Amazon S3 Vectors; Amazon Titan Text Embeddings v2 |
| [SBB-005 Tools on AgentCore Gateway with Lambda targets and the interceptor](SBB-005-tools-on-agentcore-gateway-with-lambda-targets-and-the-interceptor/index.md) | ABB-012 | Amazon Bedrock AgentCore Gateway; AWS Lambda |
| [SBB-006 Chat agent on AgentCore Runtime with Strands, Bedrock and Guardrails](SBB-006-chat-agent-on-agentcore-runtime-with-strands-bedrock-and-guardrails/index.md) | ABB-014 | Amazon Bedrock AgentCore Runtime; Strands Agents; Amazon Bedrock models (Claude); Amazon Bedrock Guardrails |
| [SBB-007 Portal API on API Gateway, Lambda and DynamoDB](SBB-007-portal-api-on-api-gateway-lambda-and-dynamodb/index.md) | ABB-019 | Amazon CloudFront; Amazon API Gateway (HTTP API); AWS Lambda; Amazon DynamoDB; AWS Secrets Manager |
| [SBB-016 Chat page on CloudFront and S3](SBB-016-chat-page-on-cloudfront-and-s3/index.md) | ABB-018 | Amazon CloudFront; Amazon S3 |
| [SBB-008 Identity on Cognito](SBB-008-identity-on-cognito/index.md) | ABB-020 | Amazon Cognito user pools |
| [SBB-009 Image build on CodeBuild and ECR](SBB-009-image-build-on-codebuild-and-ecr/index.md) | ABB-023 | AWS CodeBuild; Amazon ECR; Python 3.12 slim base image from ECR Public |
| [SBB-011 Optional projection backends: Neo4j, Apache AGE and MongoDB](SBB-011-optional-projection-backends-neo4j-apache-age-and-mongodb/index.md) | ABB-011 | Neo4j or AuraDB; PostgreSQL with Apache AGE; MongoDB or a wire-compatible service |
| [SBB-015 Command line on an operator's machine](SBB-015-command-line-on-an-operators-machine/index.md) | ABB-006, ABB-021 | Python 3.12; The knowledge-store package: rdflib, pySHACL, pypdf, PyYAML, boto3; AWS credentials or the Anthropic API |

SBB-011 is an alternative rather than a part: it replaces the in-memory projection when a collection outgrows it. The model provider, Bedrock or the Anthropic API, is an external system chosen at deployment and carried by the client inside SBB-002 and SBB-006; the Terraform module and the launch stack that provision every unit are the deployment mechanism, described in the deployment guide and on REF-001. Neither is a building block.

## Retired identifiers

Four identifiers were retired in the recalibration. An identifier is never reused.

| Retired | Was | Now | Why |
|---|---|---|---|
| SBB-010 | Terraform module with the CloudFormation launch stack | no block: provisioning | An infrastructure-as-code module provisions containers and is not one. Its content is in the deployment guide, on ABB-023 and on REF-001's deployment view |
| SBB-012 | Model access through Bedrock or the Anthropic API | no block: external system | The model provider is an external system chosen at deployment; the client that calls it is a component of SBB-002 and SBB-006, and the choice is a variation point on REF-001 |
| SBB-013 | Local profile: a folder lake, in-process tools and the local portal server | SBB-015 | A hosting profile spanning seven containers, not a container. The command line it ran is SBB-015; the local run of the sweep and the local server are that package's entry points |
| SBB-014 | The pipeline image: rdflib, pySHACL, pypdf and Claude | SBB-002 | The image and the task that runs it are one container; the image's products are now on SBB-002 |
