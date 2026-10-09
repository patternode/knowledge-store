# Quick start on AWS

Knowledge Store installs into one AWS account of yours. Terraform creates everything it runs on
(storage, the pipeline, the knowledge graph, the chat page, the agent), and CodeBuild builds its
container images inside your account. Your part is a few things before Terraform, one required
value for it, and a few things after.

This page is the short path. The [AWS installation guide](docs/deploy/aws/README.md) is the full
one, for an account with its own network, controls and domain. [Every parameter](docs/deploy/aws/parameters.md)
is listed there with its default.

> **Which version.** Use `main`. The newest tag, v0.1.2, predates the knowledge graph, the
> passage index and the chat agent described here. Once v0.2.0 is tagged, use it.

## Your part, Terraform's part

| When | You do this, in your own account | Terraform does this |
|---|---|---|
| Before | Pick a region that has Bedrock, AgentCore, S3 Vectors and Neptune (`us-east-1` has all). Enable a Claude model and Titan Text Embeddings V2 in Bedrock. Have credentials with administrator rights. | |
| Apply 1 | Give it your email (`admin_email`). Everything else has a default. | Creates the lake, network, pipeline, Neptune, the passage index, Cognito, the chat page and its API, the agent's Gateway, tools and guardrail. Starts two image builds. |
| Apply 2 | Once the images are built, set `agent = { runtime = true }`. | Creates the agent's Runtime, and the chat starts using it. |
| After | Sign in with the emailed password. Upload documents. Publish each collection's first ontology. Add people. | The pipeline extracts each upload into the knowledge graph on its own. |

There is no secret to supply. Credentials come from your environment, and Bedrock is reached
through IAM. Only if you send model calls to the Anthropic API instead do you store a key, in
Secrets Manager, and give Terraform its ARN.

## Before you start

1. **Credentials.** `export AWS_PROFILE=<profile>` for the target account, then
   `aws sts get-caller-identity` to check the account.
2. **Models.** In the Bedrock console for your region, open Model catalog and check that a Claude
   model and Amazon Titan Text Embeddings V2 are available. The first Anthropic model in an
   account asks for a short use-case form. Outside the US, find your region's inference profile id
   (`aws bedrock list-inference-profiles`) and set it as `extraction_model_id`, `chat_model_id`
   and `agent.model_id`: the default `us.anthropic.claude-sonnet-5` works only in US regions.
3. **Tools.** Terraform 1.10 or later and the AWS CLI. Python 3.12 or later, to curate ontologies.

## Install: three ways

All three deploy the same Terraform.

### From the AWS console (CloudFormation)

Nothing to install locally.

1. In the CloudFormation console for your region, choose Create stack, With new resources, and
   upload [`infra/launch/knowledge-store.yaml`](infra/launch/knowledge-store.yaml).
2. Enter your email as AdminEmail. Leave the rest for a first install. (ModelId is the inference
   profile id from step 2 above.)
3. Acknowledge that the stack creates IAM resources, and create it.

The stack runs Terraform in a CodeBuild project inside your account and completes in about 15 to
30 minutes. Its outputs give the portal URL and where to upload. For the agent, update the stack
with EnableAgentRuntime set to true once its image is built. Delete the stack to remove
everything; the lake and state buckets are kept unless DeleteDataOnStackDelete is true. The build
runs with an administrator role, used only by that CodeBuild project; read the template first.

### With Terraform

```bash
git clone https://github.com/patternode/knowledge-store.git && cd knowledge-store

# once per account: a bucket for Terraform's state
cd infra/bootstrap
terraform init && terraform apply -var account_id=<your account id> -var region=<your region>
terraform output -raw backend_hcl > ../stack/backend.hcl

# the stack: one required value
cd ../stack
cp terraform.tfvars.example terraform.tfvars    # gitignored, like backend.hcl
# edit terraform.tfvars: set admin_email (and region and the model ids outside us-east-1)
terraform init -backend-config=backend.hcl
terraform apply
```

Wait for both image builds to succeed (a few minutes; the installation guide has a command that
checks them, [step 7](docs/deploy/aws/README.md#7-first-apply)). Then add
`agent = { runtime = true }` to `terraform.tfvars` and run `terraform apply` again.

### From a deployment repository of your own

To run it for real, keep your configuration and curated ontologies in a private repository of
your own, with this repository as a pinned module. Copy [`examples/deployment`](examples/deployment)
and follow its README. Nothing of yours lives in a copy of this repository, and upgrading is a
one-line change.

## Then

1. **Sign in.** Cognito emails `admin_email` a temporary password. Open the `portal_url` output,
   sign in and choose a password. Add people with `aws cognito-idp admin-create-user`; those who may
   read private sources go in the `private-readers` group ([step 10](docs/deploy/aws/README.md#10-sign-in-and-add-people)).
2. **Upload documents** to the `upload_to` output, `s3://<name>-lake-<account>/landing/<collection>/`.
   An upload starts the pipeline within about a minute. To try it, upload [`examples/space-missions`](examples/space-missions).
3. **Publish the first ontology.** Once five documents are in, the pipeline proposes an ontology
   and waits for you (curated mode). Curate and publish it:

   ```bash
   pip install ".[aws]"
   export LAKE_URI=s3://<lake bucket>                              # the lake_bucket output
   aws s3 ls $LAKE_URI/collections/default/ontology/drafts/         # the draft ids
   knowledge-store -c default ontology pull <draft id> ontology/
   # edit ontology/ontology.ttl, set owl:versionInfo "1.0.0"
   knowledge-store -c default ontology publish ontology/ --activate
   ```

   Publishing starts extraction. For an unattended first run, set `ontology_mode = "auto"` on the
   collection (OntologyMode in the console); to bring your own ontology, set `ontology_dir`.
4. **Ask.** The chat answers from the documents, every statement linked to its passage. The
   workbench beside it shows each step the agent takes, and for a question it cannot answer,
   "What would it take?" reports the ontology extensions and data it would need
   ([docs/workbench.md](docs/workbench.md)).

## What it costs idle

About 60 USD a month, for the Neptune instance that holds the knowledge graph. Set
`knowledge_graph = { enabled = false }` (EnableKnowledgeGraph in the console) for a small demo,
and the stack idles at close to nothing: no NAT gateway and no always-on compute, only S3,
CloudFront, Lambda, DynamoDB on demand, the passage index on S3 Vectors, and Fargate while a sweep
runs. Model calls are the cost that matters: each question is several, roughly 0.10 to 0.30 USD
with a Sonnet-class model. `budget = { monthly_usd = ... }` emails you before spend runs away.
