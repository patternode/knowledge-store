# Quick start on AWS

For Azure, see [docs/architectures/azure-setup.md](docs/architectures/azure-setup.md).

Three ways to install. All three deploy the same Terraform into your own AWS account, and need access to an Anthropic Claude model in Amazon Bedrock (Bedrock console, Model access) in the region you deploy to.

## Option 1: from the AWS console (CloudFormation)

Nothing to install locally.

1. Open the CloudFormation console in your target region, choose Create stack, With new resources, and upload [`infra/launch/knowledge-store.yaml`](infra/launch/knowledge-store.yaml) (or use the release's Launch Stack link, which opens the same template).
2. Enter your email as AdminEmail. Leave everything else as it is for a first install.
3. Acknowledge that the stack creates IAM resources, and create it.

The stack runs the Terraform in a CodeBuild project inside your account and completes when Terraform has, in about 15 minutes. Its outputs give the portal URL and where to upload. Cognito emails you a temporary password.

Change settings later with Update stack: the same build applies the change. Delete the stack to remove everything Terraform created. The data lake bucket and the Terraform state bucket are kept unless you first update the stack with DeleteDataOnStackDelete set to true.

The build runs with an administrator role, because Terraform creates IAM roles, CloudFront, Cognito, Lambda, ECS and AgentCore resources. The role is used only by that CodeBuild project; review [`infra/launch/knowledge-store.yaml`](infra/launch/knowledge-store.yaml) before launching.

## Option 2: with Terraform

You need Terraform 1.10 or later and AWS credentials for the target account.

```bash
cd infra/bootstrap
terraform init && terraform apply -var account_id=<your account id>
terraform output -raw backend_hcl > ../stack/backend.hcl
cd ../stack
echo 'admin_email = "you@example.org"' > terraform.tfvars
terraform init -backend-config=backend.hcl
terraform apply
```

## Option 3: from a deployment repository of your own

To run it for real, keep your configuration and curated ontologies in a private repository of your own, with this repository as a pinned module. Copy [`examples/deployment`](examples/deployment) and follow its README.

## Then

1. Upload documents to the `upload_to` location, `s3://<name>-lake-<account>/landing/<collection>/`.
   The upload starts the pipeline within about a minute (S3 event, EventBridge, SQS, an
   EventBridge Pipe, then an ECS Fargate task).
2. The first run proposes an ontology and waits for you (curated mode). The portal's Overview shows the draft; curate and publish it:

   ```bash
   pip install ".[aws]"
   export LAKE_URI=s3://<lake bucket>
   knowledge-store -c default ontology pull <draft id> ontology/
   # edit ontology/ontology.ttl, set owl:versionInfo "1.0.0"
   knowledge-store -c default ontology publish ontology/ --activate
   ```

   Publishing starts extraction. For an unattended first run, choose OntologyMode auto (or `ontology_mode = "auto"` on the collection).
3. Open the portal and sign in.

To try it with sample content, run `python examples/sherlock-holmes/fetch.py` and upload the stories, or upload `examples/space-missions/`.

## The chat agent

The first deploy builds the agent's image. Once it is built (a few minutes; the `agent.image_project` output names the CodeBuild project), set EnableAgentRuntime to true (or `agent = { runtime = true }`) and deploy again. Until then the chat answers with the portal's own tool loop. How the agent answers, and the checks on every answer, are in [docs/architectures/aws.md](docs/architectures/aws.md).

## What it costs idle

About 70 USD a month, for the Neptune instance that holds the knowledge graph. Set EnableKnowledgeGraph to false (or `knowledge_graph = { enabled = false }`) for a small demo, and the stack idles at close to nothing: no NAT gateway and no always-on compute, only S3, CloudFront, Lambda, DynamoDB on demand, the Knowledge Base on S3 Vectors, and Fargate while a sweep runs. Model calls in Bedrock are the cost that matters.
