# Your deployment of Knowledge Store. Copy this directory into a private repository of your own and
# edit it: this file is the whole configuration, committed, and the module is pinned to a release.
# To upgrade, change ref and plan.

terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 6.66" }
    archive = { source = "hashicorp/archive", version = "~> 2.7" }
  }

  # Bucket, region and (if you use one) profile come from backend.hcl:
  #   terraform init -backend-config=backend.hcl
  # The S3 backend does not use the provider's profile, so set it there too if you need one.
  backend "s3" {
    key          = "knowledge-store/terraform.tfstate"
    use_lockfile = true
    encrypt      = true
  }
}

provider "aws" {
  region = "us-east-1"
  # profile = "my-profile"                 # or leave unset to use the environment's credentials
  # allowed_account_ids = ["123456789012"] # refuse to apply anywhere else

  default_tags {
    tags = { project = "knowledge-store", managed-by = "terraform", stack = "knowledge-store" }
  }
}

module "knowledge_store" {
  source = "git::https://github.com/patternode/knowledge-store.git//infra/modules/knowledge-store?ref=v0.1.0"

  admin_email = "you@example.org"
  name        = "knowledge-store"

  # One entry per corpus, each with its own ontology. Uploads go to landing/<id>/ in the lake.
  collections = {
    default = {
      profile = {
        name        = "My documents"
        description = "What the collection is about, in a sentence or two. It guides prompts and the portal."
      }
      # ontology_mode = "auto"   # publish the first discovered ontology unreviewed
      # ontology_dir  = "ontology/default"   # bring your own ontology instead (see ontology/README.md)
    }
  }

  # llm_provider        = "bedrock"
  # extraction_model_id = "us.anthropic.claude-sonnet-5"
  # chat_model_id       = "us.anthropic.claude-sonnet-5"
  # portal_title        = "Knowledge Store"

  # The example agent. First apply with enabled = true; once CodeBuild has pushed the agent image,
  # set runtime = true and apply again. See examples/agent in the Knowledge Store repository.
  # agent = { enabled = true, runtime = false }
}
