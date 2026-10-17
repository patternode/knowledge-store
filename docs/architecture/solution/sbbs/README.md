# Solution building blocks

The technologies chosen to realise each architecture building block: what was built or bought, and why. Fourteen, as deployed at 0.3.0. The register is [../sbbs.csv](../sbbs.csv).

| SBB | Realises | Products |
|---|---|---|
| [SBB-001 Lake on S3](SBB-001-lake-on-s3/index.md) | ABB-002 | Amazon S3 |
| [SBB-002 Sweep on ECS Fargate with EventBridge, SQS, Pipes and Scheduler](SBB-002-sweep-on-ecs-fargate-with-eventbridge-sqs-pipes-and-scheduler/index.md) | ABB-004 | Amazon ECS on AWS Fargate; Amazon EventBridge, EventBridge Pipes and Scheduler; Amazon SQS |
| [SBB-003 Knowledge graph on Amazon Neptune](SBB-003-knowledge-graph-on-amazon-neptune/index.md) | ABB-011 | Amazon Neptune Database |
| [SBB-004 Passage index on Bedrock Knowledge Base with S3 Vectors](SBB-004-passage-index-on-bedrock-knowledge-base-with-s3-vectors/index.md) | ABB-013 | Amazon Bedrock Knowledge Bases; Amazon S3 Vectors; Amazon Titan Text Embeddings v2 |
| [SBB-005 Tools on AgentCore Gateway with Lambda targets and the interceptor](SBB-005-tools-on-agentcore-gateway-with-lambda-targets-and-the-interceptor/index.md) | ABB-012, ABB-013, ABB-020 | Amazon Bedrock AgentCore Gateway; AWS Lambda |
| [SBB-006 Chat agent on AgentCore Runtime with Strands, Bedrock and Guardrails](SBB-006-chat-agent-on-agentcore-runtime-with-strands-bedrock-and-guardrails/index.md) | ABB-014, ABB-015, ABB-016, ABB-017 | Amazon Bedrock AgentCore Runtime; Strands Agents; Amazon Bedrock models (Claude); Amazon Bedrock Guardrails |
| [SBB-007 Portal on CloudFront, API Gateway, Lambda and DynamoDB](SBB-007-portal-on-cloudfront-api-gateway-lambda-and-dynamodb/index.md) | ABB-018, ABB-019, ABB-016, ABB-017, ABB-012, ABB-014, ABB-020 | Amazon CloudFront; Amazon API Gateway (HTTP API); AWS Lambda; Amazon DynamoDB; AWS Secrets Manager |
| [SBB-008 Identity on Cognito](SBB-008-identity-on-cognito/index.md) | ABB-020 | Amazon Cognito user pools |
| [SBB-009 Image build on CodeBuild and ECR](SBB-009-image-build-on-codebuild-and-ecr/index.md) | ABB-023 | AWS CodeBuild; Amazon ECR; Python 3.12 slim base image from ECR Public |
| [SBB-010 Terraform module with the CloudFormation launch stack](SBB-010-terraform-module-with-the-cloudformation-launch-stack/index.md) | ABB-023 | HashiCorp Terraform 1.14; AWS CloudFormation; AWS Budgets |
| [SBB-011 Optional projection backends: Neo4j, Apache AGE and MongoDB](SBB-011-optional-projection-backends-neo4j-apache-age-and-mongodb/index.md) | ABB-011 | Neo4j or AuraDB; PostgreSQL with Apache AGE; MongoDB or a wire-compatible service |
| [SBB-012 Model access through Bedrock or the Anthropic API](SBB-012-model-access-through-bedrock-or-the-anthropic-api/index.md) | ABB-022, ABB-005, ABB-009, ABB-014 | Amazon Bedrock (Claude models, inference profiles); Anthropic API |
| [SBB-013 Local profile: a folder lake, in-process tools and the local portal server](SBB-013-local-profile-a-folder-lake-in-process-tools-and-the-local-portal-server/index.md) | ABB-002, ABB-004, ABB-012, ABB-014, ABB-019, ABB-021, ABB-023 | Python 3.12; rdflib, pySHACL, pypdf, PyYAML; The Anthropic API or AWS credentials |
| [SBB-014 The pipeline image: rdflib, pySHACL, pypdf and Claude](SBB-014-the-pipeline-image-rdflib-pyshacl-pypdf-and-claude/index.md) | ABB-001, ABB-003, ABB-005, ABB-006, ABB-007, ABB-008, ABB-009, ABB-010, ABB-011 | rdflib; pySHACL; pypdf; PyYAML; boto3; Claude through the model client |

Two of them are alternatives rather than parts: SBB-011 replaces the in-memory projection when a collection outgrows it, and SBB-013 replaces the AWS deployment on one machine. SBB-012 is a choice between two providers made at deployment.
