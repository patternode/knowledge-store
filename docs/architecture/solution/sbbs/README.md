# Solution building blocks

The technologies chosen to realise each architecture building block: what was built or bought, and why. Fifteen at container grain, one per ABB with SBB-011 as the alternative graph, as deployed at 0.3.0 and recalibrated on 2026-10-17 under the [building block calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md). The register is [../sbbs.csv](../sbbs.csv), which also keeps the retired identifiers so they are never reused.

<div className="ks-cards">
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">SBB-001</span> <span className="ks-card__tag">realises ABB-002</span></p>

#### [Lake on S3](SBB-001-lake-on-s3/index.md)

One versioned, encrypted, TLS-only S3 bucket as the record, with EventBridge notifications so uploads start the sweep.

<ul className="ks-card__products"><li>Amazon S3</li></ul>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">SBB-002</span> <span className="ks-card__tag">realises ABB-024</span></p>

#### [Pipeline image on ECS Fargate with EventBridge, SQS, Pipes and Scheduler](SBB-002-pipeline-image-on-ecs-fargate-with-eventbridge-sqs-pipes-and-scheduler/index.md)

The pipeline as one image, built in the account from the deployed source, run as a Fargate task started by uploads through SQS and Pipes and by a schedule, with its lock in the lake.

<ul className="ks-card__products"><li>Amazon ECS on AWS Fargate</li><li>Amazon EventBridge, EventBridge Pipes and Scheduler</li><li>Amazon SQS</li><li>rdflib, pySHACL, pypdf, PyYAML, boto3</li><li>Claude through the model client</li></ul>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">SBB-003</span> <span className="ks-card__tag">realises ABB-011</span></p>

#### [Knowledge graph on Amazon Neptune](SBB-003-knowledge-graph-on-amazon-neptune/index.md)

The gold RDF as it is, in a SPARQL store the graph tools query read-only, in private subnets.

<ul className="ks-card__products"><li>Amazon Neptune Database</li></ul>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">SBB-004</span> <span className="ks-card__tag">realises ABB-013</span></p>

#### [Passage index on Bedrock Knowledge Base with S3 Vectors](SBB-004-passage-index-on-bedrock-knowledge-base-with-s3-vectors/index.md)

Search of passages by meaning at cents a month at rest, with the passage as the unit so a hit is a passage id.

<ul className="ks-card__products"><li>Amazon Bedrock Knowledge Bases</li><li>Amazon S3 Vectors</li><li>Amazon Titan Text Embeddings v2</li></ul>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">SBB-005</span> <span className="ks-card__tag">realises ABB-012</span></p>

#### [Graph tools on Lambda behind the AgentCore Gateway](SBB-005-graph-tools-on-lambda-behind-the-agentcore-gateway/index.md)

The graph and structured toolset as one Lambda in the private subnets, registered as a target of the AgentCore Gateway with its schema uploaded by Terraform.

<ul className="ks-card__products"><li>AWS Lambda</li><li>Amazon Bedrock AgentCore Gateway (as the front)</li></ul>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">SBB-015</span> <span className="ks-card__tag">realises ABB-025</span></p>

#### [Passage tools on Lambda behind the AgentCore Gateway](SBB-015-passage-tools-on-lambda-behind-the-agentcore-gateway/index.md)

The passages toolset as one Lambda outside the VPC, registered as a target of the AgentCore Gateway.

<ul className="ks-card__products"><li>AWS Lambda</li><li>Amazon Bedrock AgentCore Gateway (as the front)</li></ul>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">SBB-016</span> <span className="ks-card__tag">realises ABB-026</span></p>

#### [Tool gateway on Amazon Bedrock AgentCore Gateway](SBB-016-tool-gateway-on-amazon-bedrock-agentcore-gateway/index.md)

The managed MCP front over the two tool Lambdas: verifies the caller's token, runs the interceptor, routes to the target.

<ul className="ks-card__products"><li>Amazon Bedrock AgentCore Gateway</li></ul>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">SBB-017</span> <span className="ks-card__tag">realises ABB-027</span></p>

#### [Call interceptor on Lambda](SBB-017-call-interceptor-on-lambda/index.md)

The interceptor the gateway invokes before every tool call, as one small Lambda with no store access.

<ul className="ks-card__products"><li>AWS Lambda</li></ul>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">SBB-006</span> <span className="ks-card__tag">realises ABB-014</span></p>

#### [Chat agent on AgentCore Runtime with Strands, Bedrock and Guardrails](SBB-006-chat-agent-on-agentcore-runtime-with-strands-bedrock-and-guardrails/index.md)

The answering agent as a container on AgentCore Runtime, acting only as its caller, with the checks, the valves, the guardrail and the recorder in the same process.

<ul className="ks-card__products"><li>Amazon Bedrock AgentCore Runtime</li><li>Strands Agents</li><li>Amazon Bedrock models (Claude)</li><li>Amazon Bedrock Guardrails</li></ul>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">SBB-007</span> <span className="ks-card__tag">realises ABB-019</span></p>

#### [Portal API on API Gateway, Lambda and DynamoDB](SBB-007-portal-api-on-api-gateway-lambda-and-dynamodb/index.md)

The Chat API as one Lambda behind an HTTP API with a DynamoDB table for chat state, quota and usage, reached only through the edge with the origin secret.

<ul className="ks-card__products"><li>Amazon API Gateway (HTTP API)</li><li>AWS Lambda</li><li>Amazon DynamoDB</li><li>AWS Secrets Manager</li></ul>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">SBB-018</span> <span className="ks-card__tag">realises ABB-018</span></p>

#### [Chat page on CloudFront](SBB-018-chat-page-on-cloudfront/index.md)

The chat page as static objects in a private bucket served by CloudFront, with /api/* routed to the API behind the same distribution.

<ul className="ks-card__products"><li>Amazon CloudFront</li><li>Amazon S3 (the site bucket)</li></ul>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">SBB-008</span> <span className="ks-card__tag">realises ABB-020</span></p>

#### [Identity on Cognito](SBB-008-identity-on-cognito/index.md)

Sign-in for people and the token the whole chain verifies, or, in site mode, the service clients the portal uses on a person's behalf.

<ul className="ks-card__products"><li>Amazon Cognito user pools</li></ul>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">SBB-011</span> <span className="ks-card__tag">realises ABB-011</span></p>

#### [Optional projection backends: Neo4j, Apache AGE and MongoDB](SBB-011-optional-projection-backends-neo4j-apache-age-and-mongodb/index.md)

Backends for a collection that has outgrown one process's memory, each behind the same port and filled by the sweep, none required.

<ul className="ks-card__products"><li>Neo4j or AuraDB</li><li>PostgreSQL with Apache AGE</li><li>MongoDB or a wire-compatible service</li></ul>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">SBB-013</span> <span className="ks-card__tag">realises ABB-028</span></p>

#### [Command line on Python, the local profile](SBB-013-command-line-on-python-the-local-profile/index.md)

The command line installed from the package on an operator's machine, running the whole store on a folder or against a deployment's bucket.

<ul className="ks-card__products"><li>Python 3.12</li><li>rdflib, pySHACL, pypdf, PyYAML</li><li>The Anthropic API or AWS credentials for Bedrock</li></ul>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">SBB-019</span> <span className="ks-card__tag">realises ABB-021</span></p>

#### [Evaluation runner on Python](SBB-019-evaluation-runner-on-python/index.md)

The evaluation runner as a command in the same package, run by an evaluator against a lake or a deployed chat.

<ul className="ks-card__products"><li>Python 3.12</li></ul>

</div>
</div>
Retired in the calibration: SBB-009 Image build on CodeBuild and ECR, SBB-010 Terraform module with the CloudFormation launch stack, SBB-012 Model access through Bedrock or the Anthropic API, SBB-014 The pipeline image: rdflib, pySHACL, pypdf and Claude. The image build and the Terraform module are not blocks (an infrastructure-as-code module provisions containers and nodes; those are the blocks), the models are an external system, and the pipeline image and the task that runs it are one container, SBB-002. SBB-011 replaces Neptune when a deployment chooses another graph; SBB-013 and SBB-019 are the two commands of an operator's machine.
