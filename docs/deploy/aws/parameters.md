# Parameters

Every input of [`infra/stack`](../../../infra/stack), the root you apply. Set them in
`infra/stack/terraform.tfvars` (start from
[`terraform.tfvars.example`](../../../infra/stack/terraform.tfvars.example)). Only `admin_email`
is required. A deployment repository of your own ([`examples/deployment`](../../../examples/deployment))
passes the same inputs to the module, except `region`, `account_id`, `aws_profile` and
`extra_tags`, which belong to its provider block there.

In short: `admin_email` is required; outside US regions, so are the three model ids (the default
`us.` inference profile works only in US regions). Everything else has a default that works in a
sandbox account; the [worksheet](#worksheet) lists what an organisation usually decides.

Two other kinds of input sit outside `terraform.tfvars`:

- **Credentials** come from the environment (`AWS_PROFILE`, or the CI runner's role). They are
  never written to a file in the repository.
- **The state location** goes in `infra/stack/backend.hcl` (`bucket`, `region`, and optionally `key`).

## Worksheet

Copy this table, fill in the right-hand column, and keep it with the deployment's records.

| Decision | Parameter | Your value |
|---|---|---|
| AWS account id | `account_id` | |
| Region | `region` | |
| Resource name prefix (unique in the account) | `name` | |
| First user's email | `admin_email` | |
| Terraform state bucket and region | `backend.hcl` | |
| Claude inference profile id for the region | `extraction_model_id`, `chat_model_id`, `agent.model_id` | |
| Network: own VPC (CIDR), or existing VPC and subnets | `network` | |
| NAT gateway allowed? | `network.enable_nat` | |
| Portal domain and its us-east-1 certificate | `portal_domain` | |
| Sign-in: the stack's Cognito pool, or a host website's grant (its origin, keys, lab name, roles) | `site_sign_in` | |
| IAM permissions boundary | `permissions_boundary` | |
| Required tags | `extra_tags` | |
| Log retention, in days | `log_retention_days` | |
| Monthly budget alert and who receives it | `budget` | |
| Neptune on (about 60 USD a month), or off for a demo | `knowledge_graph.enabled` | |
| Collections: ids, names, descriptions | `collections` | |
| Ontology per collection: curated, auto, or your own | `collections.<id>.ontology_mode`, `ontology_dir` | |
| Portal title | `portal_title` | |
| Questions per person per day | `daily_questions` | |

## Account, region and naming

| Parameter | Default | Description |
|---|---|---|
| `admin_email` | required | The first portal user. Cognito emails them a temporary password. |
| `region` | `us-east-1` | Where everything is deployed. It must offer Bedrock (Claude and Titan Text Embeddings V2), AgentCore, S3 Vectors, Knowledge Bases and Neptune. |
| `name` | `knowledge-store` | The prefix of every resource name; 3 to 25 lower case letters, digits and hyphens, starting with a letter. Buckets are `<name>-lake-<account>`, `<name>-site-<account>` and so on. Must be unique in the account, and cannot change after the first apply. |
| `account_id` | empty | A guard: when set, Terraform refuses to apply with credentials for any other account. |
| `aws_profile` | empty | A named AWS CLI profile. Prefer `AWS_PROFILE` in the environment, which the S3 backend also uses. |
| `extra_tags` | `{}` | Tags added to every resource, on top of `project`, `managed-by` and `stack`. |

## Network

| Parameter | Default | Description |
|---|---|---|
| `network.cidr` | `10.42.0.0/16` | The range of the VPC the stack creates. Choose one that does not overlap networks you peer or route to. |
| `network.az_count` | `2` | Availability zones the VPC spans (2 to 6), the first zones AWS lists for the account (in practice a, b, c, ...). Neptune needs two, and needs capacity for its instance class in one of them; if the first apply reports no capacity and names a zone, raise this until that zone is included. |
| `network.enable_nat` | `false` | A NAT gateway (about 33 USD a month). The pipeline's tasks then run in private subnets with no public IP. Without it, they run in public subnets with a public IP and only egress allowed. |
| `network.existing` | none | Use a VPC you already have instead of creating one. Its fields are below. Set it, and the cidr, az_count and enable_nat fields are ignored. |
| `network.existing.vpc_id` | | The VPC. |
| `network.existing.private_subnet_ids` | | Two or more subnets in different zones for Neptune and the graph tools. They must reach S3 (a gateway endpoint on their route table, or a NAT). |
| `network.existing.pipeline_subnet_ids` | | Subnets for the pipeline's Fargate tasks. They must reach Bedrock (or the Anthropic API), ECR and S3. |
| `network.existing.pipeline_public_ip` | `false` | `true` for public subnets reached through an internet gateway; `false` for private subnets with a NAT or VPC endpoints. |

## Portal and sign-in

| Parameter | Default | Description |
|---|---|---|
| `portal_title` | `Knowledge Store` | The name in the portal's header. |
| `portal_domain.name` | empty | A domain of your own for the portal. Leave empty to use CloudFront's domain only. |
| `portal_domain.certificate_arn` | empty | An ACM certificate covering that name, in `us-east-1` (CloudFront requires it there). Set both fields or neither. |
| `admin_private` | `true` | Put the admin user in `private-readers`, the group that may read private sources. |
| `site_sign_in` | none | Sign people in on a host website instead of Cognito. The website frames the portal and hands each signed-in person's page a short grant for this lab; the portal verifies it on every request. Its fields are below. Unset, people sign in with the stack's Cognito pool. |
| `site_sign_in.issuer` | | The website's origin (`https://host`, no path): the grants' issuer, and the one site allowed to frame the portal. |
| `site_sign_in.jwks` | | The website's public grant keys, a JWKS document (for example the website's `/api/jwks.json`). P-256 keys only. To rotate, add the new key here before the website signs with it. |
| `site_sign_in.lab` | `knowledge` | The name a grant's audience must carry (`lab:<lab>`), so a grant for another lab is refused. |
| `site_sign_in.roles` | `["owner", "team", "preview"]` | Roles that may read public sources. A person with none of these roles, nor a private one, is refused. |
| `site_sign_in.private_roles` | `["owner"]` | Roles that may also read private sources. |
| `daily_questions` | `30` | Questions each person may ask per day. |

## Organisation controls

| Parameter | Default | Description |
|---|---|---|
| `permissions_boundary` | none | An IAM policy ARN set as the permissions boundary of every role the stack creates. It must allow what [components.md](components.md#iam-roles) lists. |
| `log_retention_days` | `30` | Retention of the pipeline's, the chat API's and the tools' log groups. Must be a value CloudWatch Logs accepts (1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288 or 3653). |
| `budget.monthly_usd` | `0` (none) | A monthly cost budget for the account, alerting at 80% of actual and 100% of forecast spend. |
| `budget.email` | `admin_email` | Who receives the budget alerts. |

## Models

| Parameter | Default | Description |
|---|---|---|
| `llm_provider` | `bedrock` | `bedrock` keeps every model call in your AWS account. `anthropic` sends the pipeline's and the portal's calls to the Anthropic API; the chat agent always uses Bedrock. |
| `anthropic_api_key_secret_arn` | empty | With `llm_provider = "anthropic"`: a Secrets Manager secret holding the API key. |
| `extraction_model_id` | `us.anthropic.claude-sonnet-5` | The model for discovery, review and extraction: a Bedrock inference profile id valid in your region. |
| `chat_model_id` | `us.anthropic.claude-sonnet-5` | The model of the portal's own tool loop, used until the agent runs. |

## Collections and the pipeline

| Parameter | Default | Description |
|---|---|---|
| `collections` | `{ default = {} }` | The corpora, keyed by id (1 to 40 lower case letters, digits and hyphens). Each has its own ontology, and its uploads go to `landing/<id>/`. |
| `collections.<id>.profile` | named after the id | `name`, `description`, `key_terms`, `example_questions`, `ontology_base`. It guides prompts and the portal; it is not the ontology. Set `ontology_base` to a namespace you control (the default is under `https://example.org/`). A sample question may start with `[low]`, `[medium]` or `[high]`, which the chat uses to group them and which is not part of the question. |
| `collections.<id>.sources` | an `s3_landing` source on `landing/<id>/` | Where content comes from. Built-in types: `s3_landing` (with `options.bucket` to read another bucket, which the pipeline is then granted read access to), `local_dir` and `http_urls`. Each source has a `scope`: `public` or `private`. |
| `collections.<id>.ontology_mode` | `curated` | `curated`: a person publishes each version. `auto`: the first discovered draft is published unreviewed. |
| `collections.<id>.ontology_dir` | none | Bring your own ontology: a directory, relative to `infra/stack`, holding `ontology.ttl` (with `owl:versionInfo` set) and optionally `shapes.ttl`. Discovery never runs. |
| `discovery` | `min_docs = 5, sample = 20, resamples = 2, target_classes = 15, review = true` | How discovery proposes an ontology. `review` adds a second model pass that fixes the draft's hierarchy, duplicates and domains. |
| `extraction_workers` | `4` | Documents extracted in parallel within a sweep. |
| `schedule_expression` | `rate(6 hours)` | The safety-net sweep, an EventBridge Scheduler expression. Uploads start a sweep on their own. |
| `schedule_enabled` | `true` | Turn the scheduled sweep off or on. |
| `force_destroy_lake` | `false` | Let `terraform destroy` delete the lake while it still holds objects. |

## Knowledge graph, passage index and agent

| Parameter | Default | Description |
|---|---|---|
| `knowledge_graph.enabled` | `true` | Neptune, holding the gold RDF. Off, the graph tools answer from the lake's projection in memory, which suits a small demo. |
| `knowledge_graph.instance_class` | `db.t3.medium` | The Neptune instance class. `db.t4g.medium` costs a little less but often has no capacity in a zone. |
| `knowledge_graph.serverless_min_ncu` / `serverless_max_ncu` | `0` / `8` | A minimum above zero uses Neptune Serverless instead of the instance class. |
| `knowledge_graph.deletion_protection` | `false` | Protect the cluster from deletion. The graph is rebuilt from the lake, so this is off by default. |
| `knowledge_base.enabled` | `true` | Search of passages by meaning: a Bedrock Knowledge Base on S3 Vectors. Off, passage search falls back to keywords. |
| `knowledge_base.embedding_model_id` | `amazon.titan-embed-text-v2:0` | The embedding model. Changing it after the first apply replaces the index. |
| `agent.runtime` | `false` | Create the agent's AgentCore Runtime. Set `true` on the second apply, once its image is built. |
| `agent.prod_version` | empty | Pin a tested Runtime version as the `prod` endpoint the portal calls. |
| `agent.model_id` | `us.anthropic.claude-sonnet-5` | The agent's model: a Bedrock inference profile id valid in your region. |
| `guardrail.enabled` | `true` | A Bedrock Guardrail that screens questions and checks each claim against the passages it cites. |
| `guardrail.grounding_threshold` | `0.75` | The grounding score a claim needs to be shown. |
| `valves.max_tool_calls` | `16` | Tool calls per question. |
| `valves.max_model_calls` | `14` | Model calls per question. |
| `valves.max_output_tokens` | `4000` | Output tokens per model call. |
| `valves.grounding_repairs` | `1` | Times the agent is shown its failed citations and asked again. |
| `valves.chat_concurrency` | `20` | The chat API's reserved concurrency: questions answered at once. `-1` for no reservation, `0` switches the chat off. |
