# Quick start

Two ways to install. Both deploy the same Terraform into your own AWS account, and need access to an Anthropic Claude model in Amazon Bedrock (Bedrock console, Model access) in the region you deploy to.

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
2. The first run proposes an ontology and waits for you (curated mode). The portal's Overview shows the draft; curate and publish it:

   ```bash
   pip install .
   export LAKE_URI=s3://<lake bucket>
   knowledge-store -c default ontology pull <draft id> ontology/
   # edit ontology/ontology.ttl, set owl:versionInfo "1.0.0"
   knowledge-store -c default ontology publish ontology/ --activate
   ```

   Publishing starts extraction. For an unattended first run, choose OntologyMode auto (or `ontology_mode = "auto"` on the collection).
3. Open the portal and sign in.

To try it with sample content, run `python examples/sherlock-holmes/fetch.py` and upload the stories, or upload `examples/space-missions/`.

## The example agent

Set EnableAgent to true (or `agent = { enabled = true }`), wait for the agent image to build, then set EnableAgentRuntime to true. See [examples/agent](examples/agent/README.md).
