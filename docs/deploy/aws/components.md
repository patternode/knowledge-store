# Components and their Terraform

Knowledge Store on AWS has two use cases:

- **Ingestion:** documents go in, an ontology is applied to them, and a knowledge graph comes out.
- **Chat:** a person asks a question, and an agent answers from the graph. Every statement in the
  answer links to the passage it comes from.

![Knowledge Store on AWS](architecture.png)

All of it is one Terraform module, [`infra/modules/knowledge-store`](../../../infra/modules/knowledge-store).
It is made of submodules, one per component. A root calls the module with its own provider and
backend:

- [`infra/stack`](../../../infra/stack) is the reference root, driven by `terraform.tfvars`.
- [`examples/deployment`](../../../examples/deployment) is a template for a deployment repository
  of your own, with the module pinned to a release.

```
infra/
  bootstrap/                  the Terraform state bucket (once per account; local state)
  stack/                      the root you apply: provider, backend, variables, outputs, tests
  modules/
    knowledge-store/          the module: wires the components below together
      lake/                   S3: the record
      image-build/            CodeBuild and ECR: the pipeline and agent images
      network/                VPC, subnets, S3 gateway endpoint (skipped with network.existing)
      pipeline/               ECS Fargate sweep, its triggers and schedule
      knowledge-graph/        Neptune
      knowledge-base/         Bedrock Knowledge Base on S3 Vectors
      identity/               Cognito
      portal/                 CloudFront, the chat page, API Gateway, the chat API Lambda, DynamoDB
      agent/                  AgentCore Gateway and Runtime, tool Lambdas, Bedrock Guardrail
  launch/                     a CloudFormation stack that runs the same Terraform from CodeBuild
```

## How the components connect

```
lake ──────────────► pipeline ──► knowledge-graph (Neptune, in network's private subnets)
  │                     │    └──► knowledge-base (indexes the lake's kb/passages/)
  │      image-build ───┘ (pipeline image)
  │           └──────────────────► agent (agent image)
  │
  ├──► portal ◄──── identity (Cognito issuer and client; callback URLs from portal)
  │      └───────── agent (Runtime ARN and qualifier: the portal asks the agent)
  └──► agent ◄───── knowledge-graph, knowledge-base, identity (token authorizers)
```

The module's [`main.tf`](../../../infra/modules/knowledge-store/main.tf) is short and readable.
Start there to see every connection.

## The components

### Lake: the record

| | |
|---|---|
| **Job** | Holds every layer of the data: uploads (`landing/`), immutable copies (`bronze/`), parsed documents and passages (`silver/`), the RDF per ontology version (`gold/`), the ontology's versions and drafts, and each collection's configuration. Everything else is rebuilt from it. |
| **AWS** | One S3 bucket, `<name>-lake-<account>`. Versioning is on, with old versions kept 30 days. Encrypted with SSE-S3, public access blocked, TLS required. EventBridge notifications are on. |
| **Terraform** | [`modules/lake`](../../../infra/modules/lake/main.tf): `aws_s3_bucket.lake` and its versioning, encryption, public access block, TLS-only policy and lifecycle. `aws_s3_object.collections`, `collection_config` and `collection_ontology` write each collection's sources, profile, settings and provided ontology from your variables. |
| **Your inputs** | `collections`, `discovery`, `extraction_workers`, `force_destroy_lake` |

### Image build

| | |
|---|---|
| **Job** | Builds the pipeline's image (x86_64) and the agent's image (arm64, which AgentCore Runtime requires) from this repository, inside your account. Nothing is built on the machine that runs Terraform. |
| **AWS** | An artifacts bucket `<name>-build-<account>`. Two ECR repositories, `<name>-pipeline` and `<name>-agent`, which scan on push and keep the last 10 images. Two CodeBuild projects, `<name>-image` and `<name>-agent-image`. An EventBridge rule that starts both when a new source bundle lands. |
| **Terraform** | [`modules/image-build`](../../../infra/modules/image-build/main.tf). `archive_file.source` zips the repository (Dockerfile, `pyproject.toml`, `src/`) under its content hash. The upload (`aws_s3_object.source`) starts the builds, so an unchanged source never rebuilds. |
| **Your inputs** | `name`, `permissions_boundary` |

### Network

| | |
|---|---|
| **Job** | Somewhere for the pipeline's tasks, Neptune and the graph tools to run. By default there is no NAT gateway. The pipeline's tasks run in public subnets with a public IP and only egress allowed. Neptune and the graph tools sit in private subnets with no route out, and reach S3 through a free gateway endpoint. |
| **AWS** | A VPC; public and private subnets in each zone; an internet gateway; route tables; an S3 gateway endpoint; and, with `enable_nat`, a NAT gateway with its Elastic IP. |
| **Terraform** | [`modules/network`](../../../infra/modules/network/main.tf), called as `module.network[0]`. With `network.existing` it is not called at all, and the VPC and subnets you give are used instead (`local.vpc_id`, `local.private_subnet_ids` and `local.pipeline_subnet_ids` in the module's `main.tf`). |
| **Your inputs** | `network` |

### Pipeline: the sweep

| | |
|---|---|
| **Job** | One idempotent sweep over every collection: ingest, refine, discover and review an ontology (or publish the one you provide), extract against it with SHACL validation, and project. At the end it loads the gold RDF into Neptune and writes the passages for the Knowledge Base, starting an ingestion job when any changed. |
| **AWS** | An ECS cluster `<name>` and a Fargate task definition `<name>-pipeline` (1 vCPU, 4 GB, 30 GB ephemeral storage). Two triggers start it:<br>• **Uploads:** an S3 upload to `landing/`, or a new `ontology/active.json`, goes through an EventBridge rule to an SQS queue (`<name>-uploads`, with a dead-letter queue), then an EventBridge Pipe, then ECS RunTask.<br>• **Schedule:** an EventBridge Scheduler schedule `<name>-sweep` runs it periodically as a safety net.<br>A task takes an S3 lock, so only one sweeps at a time. |
| **Terraform** | [`modules/pipeline`](../../../infra/modules/pipeline/main.tf): `aws_ecs_task_definition.pipeline`, `aws_sqs_queue.uploads`, `aws_pipes_pipe.uploads`, `aws_scheduler_schedule.sweep`, and the task's role `aws_iam_role.task`. |
| **Your inputs** | `llm_provider`, `anthropic_api_key_secret_arn`, `extraction_model_id`, `schedule_expression`, `schedule_enabled`, `network`, `log_retention_days`; collection sources that read other buckets add read grants |

### Knowledge graph: Neptune

| | |
|---|---|
| **Job** | Holds the gold RDF as it is: one named graph per document per ontology version, and one for the active ontology. The agent's graph tools query it with fixed SPARQL built from the ontology. |
| **AWS** | A Neptune cluster `<name>` with one instance (`db.t3.medium`, or Neptune Serverless). It is in the private subnets, with IAM database authentication, encrypted storage and an audit log exported to CloudWatch. Two security groups: Neptune's own, and a client group. Port 8182 is open only to the client group (the graph tools) and the pipeline's tasks. |
| **Terraform** | [`modules/knowledge-graph`](../../../infra/modules/knowledge-graph/main.tf), called with `count` so that `knowledge_graph.enabled = false` removes it. It outputs `data_arn`, the resource that the IAM `neptune-db:*` grants name. |
| **Your inputs** | `knowledge_graph` |

### Passage index: Bedrock Knowledge Base on S3 Vectors

| | |
|---|---|
| **Job** | Search of passages by meaning, for questions that describe a situation rather than name things. One passage is one vector (no chunking), so a hit is a passage id: the same id the graph's facts cite. |
| **AWS** | An S3 vector bucket `<name>-vectors-<account>` with a `passages` index (1024 dimensions, cosine). A Knowledge Base `<name>-passages` with an S3 data source on the lake's `kb/passages/`. Its service role may read only that prefix and call only the embedding model. |
| **Terraform** | [`modules/knowledge-base`](../../../infra/modules/knowledge-base/main.tf): `aws_s3vectors_index.passages`, `aws_bedrockagent_knowledge_base.this` and `aws_bedrockagent_data_source.passages`. Called with `count`, so that `knowledge_base.enabled = false` removes it. |
| **Your inputs** | `knowledge_base` |

### Identity: Cognito

| | |
|---|---|
| **Job** | Sign-in for people. Only an administrator creates users (no self sign-up). Members of `private-readers` may read private sources. |
| **AWS** | A user pool `<name>` with a password policy and email recovery. A managed sign-in domain `<name>-<account>`. One public web client: authorisation code with PKCE, no secret, 60-minute tokens. The `private-readers` group, and the admin user. |
| **Terraform** | [`modules/identity`](../../../infra/modules/identity/main.tf). Its callback URLs are the portal's URLs, both the custom domain and CloudFront's. |
| **Your inputs** | `admin_email`, `admin_private`, `portal_domain`, `site_sign_in` |

With `site_sign_in`, people sign in on a host website instead and the pool signs no one in. It still
holds two client-credentials clients, `<name>-site-public` (scopes `agent.invoke`, `tools.public`) and
`<name>-site-private` (also `tools.private`), which the portal asks the agent as on a person's behalf.

### Portal: the chat page and its API

| | |
|---|---|
| **Job** | A static chat page and its API on one URL. The API checks the person's daily quota, then answers asynchronously by asking the agent as that person, with their own access token. Until the agent runs, it answers with its own tool loop. It also gives a person a short-lived link to a source document they may read. |
| **AWS** | Three request paths:<br>• **CloudFront** serves `/*` from a private S3 bucket (`<name>-site-<account>`, through origin access control) and sends `/api/*` to API Gateway.<br>• **API Gateway** is an HTTP API with a Cognito JWT authorizer on every route, throttled to 20 requests a second.<br>• **The Lambda** is `<name>-portal-api` (Python 3.12, a zip built by Terraform), with reserved concurrency as the concurrency valve.<br>DynamoDB `<name>-chat` (on demand, with a TTL) holds answers and quotas. With `portal_domain`, CloudFront serves your domain with your ACM certificate. |
| **Terraform** | [`modules/portal`](../../../infra/modules/portal/main.tf): `aws_cloudfront_distribution.this`, `aws_apigatewayv2_*`, `aws_lambda_function.api`, `aws_dynamodb_table.chat`. `aws_s3_object.config` writes the page's `config.json` (sign-in endpoints and redirect URL). |
| **Your inputs** | `portal_title`, `portal_domain`, `daily_questions`, `valves.chat_concurrency`, `chat_model_id`, `llm_provider`, `log_retention_days` |

### Agent: Gateway, tools, guardrail and Runtime

| | |
|---|---|
| **Job** | Answers questions from the graph, as the person asking:<br>• The agent's system prompt holds the collection's ontology.<br>• It calls read-only tools through a Gateway that authenticates the person's token. An interceptor writes the person's scope into every call.<br>• It answers as claims, each citing a passage with a verbatim quote.<br>• Code checks each citation, and the guardrail checks each claim's grounding. Only claims that pass are shown. |
| **AWS** | • **Gateway:** an AgentCore Gateway `<name>-tools` (MCP, Cognito JWT authorizer) with a REQUEST interceptor Lambda `<name>-agent-interceptor`, and two targets:<br>&nbsp;&nbsp;– the graph tools Lambda `<name>-tools-graph`, in the private subnets, with read-only Neptune access<br>&nbsp;&nbsp;– the passage tools Lambda `<name>-tools-passages`, outside the VPC, which calls `bedrock:Retrieve` on the Knowledge Base<br>• **Guardrail:** a Bedrock Guardrail `<name>-chat` (prompt attack and content filters, contextual grounding) and a published version.<br>• **Runtime:** an AgentCore Runtime `<name>_chat` running the agent image, with a Cognito JWT authorizer, and optionally a `prod` endpoint pinned to a version. |
| **Terraform** | [`modules/agent`](../../../infra/modules/agent/main.tf): `aws_bedrockagentcore_gateway.this`, `aws_bedrockagentcore_gateway_target.this` (graph, passages), `aws_lambda_function.graph`, `passages` and `interceptor`, `aws_bedrock_guardrail.this`, `aws_bedrockagentcore_agent_runtime.agent` (created only with `agent.runtime = true`) and `aws_bedrockagentcore_agent_runtime_endpoint.prod`. The tools' schemas are uploaded to the lake's `agentcore/tool-schemas/`. |
| **Your inputs** | `agent`, `guardrail`, `valves`, `knowledge_graph`, `knowledge_base`, `log_retention_days` |

### Budget

| | |
|---|---|
| **Job** | Emails when the account's monthly spend reaches 80% of the budget, or is forecast to pass 100%. |
| **Terraform** | `aws_budgets_budget.monthly` in the module's `main.tf`, created only when `budget.monthly_usd > 0`. |

## Security model

- **People:** every API route needs a valid Cognito token, which API Gateway checks before the
  Lambda runs. The agent's Runtime and Gateway accept only tokens from the portal's client. The
  agent presents the person's own token to the Gateway, so it can never read more than the person
  asking. A person outside `private-readers` never sees a private source, whatever the model asks for.
- **People, signed in through a website (`site_sign_in`):** the website frames the portal and hands
  the page a short grant for this lab (ES256, about fifteen minutes). API Gateway lets requests
  through, and the portal Lambda verifies the grant on every request against the website's public
  keys: signature, issuer, audience `lab:<lab>` and expiry. The person's roles decide what they may
  read, and a person with no role this lab takes is refused. The portal then asks the agent as the
  public or the private service client, whose Gateway scopes match what the person may read. Their
  credentials are in the secret `<name>/portal/service-clients`, readable only by the portal's
  role. CloudFront lets only the website (and the portal itself) frame the pages.
- **Data:** the lake and the site bucket block public access. Only CloudFront reads the site
  bucket. Neptune has no public endpoint and requires IAM authentication. Every bucket, Neptune
  and the vector index are encrypted at rest with AWS-managed keys.
- **Network:** nothing listens on a public IP. The pipeline's tasks have egress only. Neptune
  accepts connections on 8182 from its two client groups alone.
- **Least privilege:** each role may do only its own job (below). The graph tools may only read
  Neptune; the pipeline alone writes to it.
- **Supply chain:** images are built in your account from the repository you deployed. The only
  outside pull is the Python base image from ECR Public.

## IAM roles

Every role carries `permissions_boundary` when you set one. A boundary must allow at least these
actions, or the component fails at run time.

| Role | Assumed by | May |
|---|---|---|
| `<name>-codebuild` | CodeBuild | Read the source bundle; push to the two ECR repositories; write build logs |
| `<name>-build-trigger` | EventBridge | Start the two CodeBuild projects |
| `<name>-pipeline-exec` | ECS | Pull the pipeline image; write its logs (`AmazonECSTaskExecutionRolePolicy`) |
| `<name>-pipeline-task` | the pipeline's task | Read, write and list the lake; read source buckets you configured; invoke Bedrock models; read the Anthropic key secret (if used); connect to Neptune, then read, write and delete data in it; start and get Knowledge Base ingestion jobs |
| `<name>-pipe` | EventBridge Pipes | Receive from the uploads queue; run the pipeline task; pass its two roles |
| `<name>-scheduler` | EventBridge Scheduler | Run the pipeline task; pass its two roles |
| `<name>-knowledge-base` | Bedrock | Invoke the embedding model; read the lake's `kb/` prefix; write and query the vector index |
| `<name>-portal-api` | Lambda | Read the lake's served layers; read and write the chat table; invoke Bedrock models; invoke itself (for asynchronous answers); write logs |
| `<name>-tools-graph` | Lambda | Read the lake's gold, ontology and config layers; connect to Neptune and read data only; VPC networking and logs |
| `<name>-tools-passages` | Lambda | Read the lake's gold, silver and config layers; `bedrock:Retrieve` on the Knowledge Base; logs |
| `<name>-agent-interceptor` | Lambda | Write logs |
| `<name>-gateway` | AgentCore | Invoke the two tool Lambdas and the interceptor; read the tool schemas |
| `<name>-agent-runtime` | AgentCore | Pull the agent image; invoke Bedrock models; apply the guardrail; write logs, traces and metrics |

## Names

Every name derives from `name` (and the account id, where a name must be unique across AWS):

| Resource | Name |
|---|---|
| S3 buckets | `<name>-lake-<account>`, `<name>-site-<account>`, `<name>-build-<account>`; vector bucket `<name>-vectors-<account>` |
| Cognito | user pool `<name>`, domain `<name>-<account>` |
| ECR | `<name>-pipeline`, `<name>-agent` |
| ECS | cluster `<name>`, task family `<name>-pipeline` |
| Lambda | `<name>-portal-api`, `<name>-tools-graph`, `<name>-tools-passages`, `<name>-agent-interceptor` |
| Neptune | cluster `<name>`, instance `<name>-1` |
| Bedrock | Knowledge Base `<name>-passages`, guardrail `<name>-chat` |
| AgentCore | Gateway `<name>-tools`, Runtime `<name with _ for ->_chat` |
| Other | DynamoDB `<name>-chat`; SQS `<name>-uploads`, `<name>-uploads-dlq`; schedule `<name>-sweep`; Pipe `<name>-uploads`; API `<name>-portal`; budget `<name>-monthly` |

## Outputs

| Output | What it is |
|---|---|
| `portal_url` | The chat page: your domain when `portal_domain` is set, else CloudFront's |
| `portal_cloudfront_domain` | Where your domain's DNS record must point |
| `lake_bucket`, `upload_to` | The lake, and each collection's upload location |
| `image_build_project` | The pipeline image's CodeBuild project |
| `agent` | The Runtime ARN and qualifier, Gateway URL, guardrail id and the agent image's CodeBuild project |
| `run_now` | An `aws ecs run-task` command that starts a sweep by hand |
| `pipeline_logs` | The pipeline's log group |
| `cognito_user_pool`, `cognito_client_id` | The user pool and the portal's client |
| `knowledge_graph`, `knowledge_base` | Neptune's endpoint and the Knowledge Base's ids (null when off) |
| `evaluate` | The command that runs an evaluation set against the deployed chat |
| `sign_in` | How people sign in (`cognito` or `site`), and with `site`, the lab name, the website that may frame the portal and the service clients |
| `provided_ontologies` | Collections that bring their own ontology, with the files uploaded for each |

## Tests

The Terraform is tested with mocked providers, so no AWS account is needed:

```bash
cd infra/stack
terraform init -backend=false
terraform test
```

| Test file | What it checks |
|---|---|
| [`graph_and_chat.tftest.hcl`](../../../infra/stack/tests/graph_and_chat.tftest.hcl) | Neptune and the Knowledge Base by default, a demo without them, the agent waiting for its image |
| [`ontology_dir.tftest.hcl`](../../../infra/stack/tests/ontology_dir.tftest.hcl) | A provided ontology is uploaded; a directory without `ontology.ttl` is refused |
| [`deploy_options.tftest.hcl`](../../../infra/stack/tests/deploy_options.tftest.hcl) | The default network, a NAT, an existing VPC, a custom portal domain, a permissions boundary and log retention, and the validation of each |

CI also runs `terraform fmt -check`, `terraform validate` on both roots, and `cfn-lint` on the
launch stack.
