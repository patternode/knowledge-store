# Deploying the Azure architecture from scratch

Every choice below is made for you, with the reason. Where Azure offers options, this picks the
one that is secure by default, costs least while idle, and needs the fewest moving parts. What
is built is described in [azure.md](azure.md).

## The choices

| Decision | Choice | Why |
|---|---|---|
| Tenant | Your organisation's existing Entra ID tenant | Portal users and Copilot Studio users are the people already in it |
| Subscription | A new, dedicated pay-as-you-go subscription | Its own billing, budget and access; deleting it removes everything |
| Region | East US 2, for the stack and the Foundry resource | Every service used here is offered there, including Claude in Foundry, Flex Consumption and API Management v2 |
| Profile | native first; common once it works | Nothing to sign up for beyond Azure; profile common is a tfvars change later |
| Models | Claude Sonnet 5 for extraction and chat, deployment name `claude-sonnet-5` | The prompts are tested on it; it accepts forced tool use, which extraction needs |
| Who deploys | You, signed in with the Azure CLI | Simplest for a first deployment; move to a CI pipeline with workload identity federation later |
| Curators | Your own user, by object id | App role assignment to groups needs Entra ID P1; users work on every tenant |
| Terraform state | A storage account made by `infra/azure/bootstrap` | Entra auth, no keys, every state version kept |
| Graph | Off at first, then `graph = true` | Proves the pipeline before adding a database with a monthly floor |

## 1. Prepare the subscription (once)

1. In the Azure portal, go to Subscriptions, then Add, and create a pay-as-you-go subscription
   named `knowledge-store` in your tenant. It needs a payment method that can buy Azure
   Marketplace offers (Claude in Foundry is one).
2. In Cost Management, then Budgets, add a monthly budget on the subscription with an email alert
   at 80%.
3. Check your roles. You need Owner on the subscription (you have it as its creator) and, in
   Entra ID, Application Administrator or Cloud Application Administrator (Global Administrator
   includes both), because Terraform creates app registrations.

## 2. Install the tools

- Azure CLI 2.70 or later (`winget upgrade Microsoft.AzureCLI` on Windows)
- Terraform 1.10 or later
- Python 3.12 or later, on the path as `python` (or set `python_command`)

Then sign in and select the subscription:

```bash
az login --tenant <tenant id or domain>
az account set --subscription knowledge-store
```

Register the resource providers the stack uses (the first time only):

```bash
for p in Microsoft.App Microsoft.ApiManagement Microsoft.CognitiveServices Microsoft.ContainerRegistry Microsoft.DBforPostgreSQL Microsoft.DocumentDB Microsoft.EventGrid Microsoft.KeyVault Microsoft.OperationalInsights Microsoft.Insights Microsoft.Storage Microsoft.Web; do az provider register --namespace $p; done
```

## 3. Deploy Claude in Microsoft Foundry

This is the one step Terraform cannot do for you, because deploying Claude accepts Anthropic's
marketplace terms.

1. Create a resource group for it: `az group create -n rg-knowledge-store-foundry -l eastus2`.
2. In the Foundry portal (ai.azure.com), create a project with a new Foundry resource in that
   resource group, in East US 2.
3. In the model catalog, open Claude Sonnet 5 and deploy it. Keep the deployment name
   `claude-sonnet-5` and the Global Standard deployment type, and accept the terms.
4. Try it once in the playground, so you know the deployment answers before the pipeline calls it.
5. Note the Foundry resource's name (not the project's).

Claude in Foundry is sold and operated by Anthropic, which is the data processor for prompts and
outputs. Read the terms in the catalog before you send it anything sensitive.

## 4. Create the state storage

```bash
cd infra/azure/bootstrap
terraform init
terraform apply -var subscription_id=$(az account show --query id -o tsv)
terraform output -raw backend_hcl > ../stack/backend.hcl
```

## 5. Configure and apply the stack

```bash
cd ../stack
cp terraform.tfvars.example terraform.tfvars
az ad signed-in-user show --query id -o tsv     # your object id, for admin_principal_ids
```

Fill in `subscription_id`, `admin_principal_ids`, `publisher_email` and `foundry`
(`resource_name` from step 3, `resource_group_name = "rg-knowledge-store-foundry"`). Add a
collection if you like; the default is one called `default`. Then:

```bash
terraform init -backend-config=backend.hcl
terraform apply
```

The first apply takes 15 to 30 minutes. It builds the pipeline image in Azure and packages the
Function App on your machine (the first time downloads its dependencies). If it stops with a 403
on a storage blob or a secret, a role assignment had not reached the data plane yet: run
`terraform apply` again.

## 6. Use it

```bash
terraform output portal_url
terraform output upload_to
```

Upload documents with your own sign-in (the stack gave you Storage Blob Data Contributor on the
lake):

```bash
az storage blob upload-batch --auth-mode login --account-name <account> --destination lake --destination-path landing/default --source ./my-documents
```

Uploads start the pipeline job within about a minute. Watch it with
`az containerapp job execution list -n knowledge-store-uploads -g rg-knowledge-store -o table`.
Open the portal URL and sign in with your organisation account.

With `ontology_mode = "curated"` (the default) the first run stops after discovery with a draft.
Curate and publish it from your machine, signed in with the Azure CLI:

```bash
export LAKE_URI=$(terraform output -raw lake_uri)   # in infra/azure/stack
cd ../../..                                          # the repository root
pip install -e ".[azure]"
knowledge-store ontology pull <draft id> ontology/
knowledge-store ontology publish ontology/ --activate
```

## 7. Turn on the graph and the document projection

Set `graph = true` and `document_projection = true` in terraform.tfvars and apply. The next
sweep loads both; start one now with
`az containerapp job start -n knowledge-store-schedule -g rg-knowledge-store`.

## 8. Profile common (Atlas and AuraDB)

1. MongoDB Atlas: create an organisation and a project, then a cluster on Azure in East US 2
   (the free tier where Atlas offers it on Azure for trying; a dedicated tier for real use). Add
   a database user with a generated password. Container Apps and Flex Consumption have no fixed
   outbound addresses without a virtual network, so for a trial allow access from anywhere and
   rely on the password and TLS; for production use Private Link, which needs the stack's
   virtual network integration (not built yet).
2. Neo4j AuraDB: create an AuraDB Professional instance on Azure in East US 2 and download the
   credentials file at once (the password is shown only once).
3. In terraform.tfvars set `profile = "common"`, `mongodb_uri`, `graph = true`, `neo4j` and
   `neo4j_password`, and apply. Keep terraform.tfvars out of git (it is ignored) or pass the
   secrets as `TF_VAR_mongodb_uri` and `TF_VAR_neo4j_password`.

## 9. Prepare Copilot Studio

The agent itself is not built yet; this prepares where it will live.

1. In the Power Platform admin center, create an environment named `Knowledge Store`, type
   Sandbox, region United States (matching East US 2), with a Dataverse database.
2. Under Billing, then Billing plans, create a pay-as-you-go plan linked to the `knowledge-store`
   subscription and select the new environment. Copilot Studio usage then bills to Azure, with
   no licences to buy.
3. Under Policies, then Data policies, check that no policy blocks custom connectors in that
   environment.
4. Install the Power Platform CLI (`dotnet tool install --global Microsoft.PowerApps.CLI.Tool`)
   and run `pac auth create --environment <environment URL>`.

The stack already created what the connector needs: `terraform output mcp_url`,
`terraform output entra` and `terraform output -raw copilot_client_secret`.

## Taking it down

`terraform destroy` removes everything except the lake, which a delete lock protects. To remove
the lake too, set `force_destroy_lake = true`, apply, then destroy. The Foundry resource and the
state storage are outside the stack; delete their resource groups by hand.
