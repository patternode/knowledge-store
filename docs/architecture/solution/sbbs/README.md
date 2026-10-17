# Solution building blocks

The technologies chosen to realise each architecture building block: what was built or bought, and why. Fifteen at container grain, one per ABB with SBB-011 as the alternative graph, as deployed at 0.3.0 and recalibrated on 2026-10-17 under the [building block calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md). The register is [../sbbs.csv](../sbbs.csv), which also keeps the retired identifiers so they are never reused.

| SBB | Realises | Products |
|---|---|---|
| [SBB-001 Lake on S3](SBB-001-lake-on-s3/index.md) | ABB-002 | Amazon S3 |
| [SBB-002 Pipeline image on ECS Fargate with EventBridge, SQS, Pipes and Scheduler](SBB-002-pipeline-image-on-ecs-fargate-with-eventbridge-sqs-pipes-and-scheduler/index.md) | ABB-024 | Amazon ECS on AWS Fargate; Amazon EventBridge, EventBridge Pipes and Scheduler; Amazon SQS; rdflib, pySHACL, pypdf, PyYAML, boto3; Claude through the model client |
| [SBB-003 Knowledge graph on Amazon Neptune](SBB-003-knowledge-graph-on-amazon-neptune/index.md) | ABB-011 | Amazon Neptune Database |
| [SBB-004 Passage index on Bedrock Knowledge Base with S3 Vectors](SBB-004-passage-index-on-bedrock-knowledge-base-with-s3-vectors/index.md) | ABB-013 | Amazon Bedrock Knowledge Bases; Amazon S3 Vectors; Amazon Titan Text Embeddings v2 |
| [SBB-005 Graph tools on Lambda behind the AgentCore Gateway](SBB-005-graph-tools-on-lambda-behind-the-agentcore-gateway/index.md) | ABB-012 | AWS Lambda; Amazon Bedrock AgentCore Gateway (as the front) |
| [SBB-015 Passage tools on Lambda behind the AgentCore Gateway](SBB-015-passage-tools-on-lambda-behind-the-agentcore-gateway/index.md) | ABB-025 | AWS Lambda; Amazon Bedrock AgentCore Gateway (as the front) |
| [SBB-016 Tool gateway on Amazon Bedrock AgentCore Gateway](SBB-016-tool-gateway-on-amazon-bedrock-agentcore-gateway/index.md) | ABB-026 | Amazon Bedrock AgentCore Gateway |
| [SBB-017 Call interceptor on Lambda](SBB-017-call-interceptor-on-lambda/index.md) | ABB-027 | AWS Lambda |
| [SBB-006 Chat agent on AgentCore Runtime with Strands, Bedrock and Guardrails](SBB-006-chat-agent-on-agentcore-runtime-with-strands-bedrock-and-guardrails/index.md) | ABB-014 | Amazon Bedrock AgentCore Runtime; Strands Agents; Amazon Bedrock models (Claude); Amazon Bedrock Guardrails |
| [SBB-007 Portal API on API Gateway, Lambda and DynamoDB](SBB-007-portal-api-on-api-gateway-lambda-and-dynamodb/index.md) | ABB-019 | Amazon API Gateway (HTTP API); AWS Lambda; Amazon DynamoDB; AWS Secrets Manager |
| [SBB-018 Chat page on CloudFront](SBB-018-chat-page-on-cloudfront/index.md) | ABB-018 | Amazon CloudFront; Amazon S3 (the site bucket) |
| [SBB-008 Identity on Cognito](SBB-008-identity-on-cognito/index.md) | ABB-020 | Amazon Cognito user pools |
| [SBB-011 Optional projection backends: Neo4j, Apache AGE and MongoDB](SBB-011-optional-projection-backends-neo4j-apache-age-and-mongodb/index.md) | ABB-011 | Neo4j or AuraDB; PostgreSQL with Apache AGE; MongoDB or a wire-compatible service |
| [SBB-013 Command line on Python, the local profile](SBB-013-command-line-on-python-the-local-profile/index.md) | ABB-028 | Python 3.12; rdflib, pySHACL, pypdf, PyYAML; The Anthropic API or AWS credentials for Bedrock |
| [SBB-019 Evaluation runner on Python](SBB-019-evaluation-runner-on-python/index.md) | ABB-021 | Python 3.12 |

Retired in the calibration: SBB-009 Image build on CodeBuild and ECR, SBB-010 Terraform module with the CloudFormation launch stack, SBB-012 Model access through Bedrock or the Anthropic API, SBB-014 The pipeline image: rdflib, pySHACL, pypdf and Claude. The image build and the Terraform module are not blocks (an infrastructure-as-code module provisions containers and nodes; those are the blocks), the models are an external system, and the pipeline image and the task that runs it are one container, SBB-002. SBB-011 replaces Neptune when a deployment chooses another graph; SBB-013 and SBB-019 are the two commands of an operator's machine.
