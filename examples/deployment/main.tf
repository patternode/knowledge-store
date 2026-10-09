# Your deployment of Knowledge Store. Copy this directory into a private repository of your own and
# edit it: this file is the whole configuration, committed, and the module is pinned to a release
# (here, until the next release is tagged, to the commit on main that carries the GraphRAG
# architecture). To upgrade, change ref and plan. Every input: docs/deploy/aws/parameters.md.

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
  source = "git::https://github.com/patternode/knowledge-store.git//infra/modules/knowledge-store?ref=3c6948a5ca410ae2fab829e1f339156aa481bc17"

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
      # Structured lookup is on when that directory also holds mappings.yaml. A collection
      # without it is unchanged. The space-missions sample is examples/space-missions.
    }
  }

  # llm_provider        = "bedrock"
  # anthropic_api_key_secret_arn = "arn:aws:secretsmanager:..."  # with "anthropic": the key's secret, never the key (README.md)
  # extraction_model_id = "us.anthropic.claude-sonnet-5"
  # chat_model_id       = "us.anthropic.claude-sonnet-5"
  # portal_title        = "Knowledge Store"

  # The chat agent. The first apply builds its image; once CodeBuild has pushed it, set runtime =
  # true and apply again. Until then the portal answers with its own tool loop.
  # agent = { runtime = true }

  # knowledge_graph = { enabled = true }      # Neptune (db.t3.medium, about 60 USD a month); false answers from memory
  # knowledge_base  = { enabled = true }      # search passages by meaning (Bedrock Knowledge Base on S3 Vectors)
  # guardrail       = { enabled = true, grounding_threshold = 0.75 }
  # valves          = { max_tool_calls = 16, max_model_calls = 14, chat_concurrency = 20 }
  # daily_questions = 30                     # per person
  # budget          = { monthly_usd = 200 }  # a monthly cost budget mailed to admin_email
}
