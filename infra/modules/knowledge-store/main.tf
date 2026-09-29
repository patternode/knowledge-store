# The Knowledge Store module: everything, in one apply. A root calls it with its own provider
# and backend: infra/stack is the reference root, examples/deployment a template for your own.
#
#   lake      the bucket, layered by prefix, with the deployer's sources/profile/settings
#   build     CodeBuild builds the pipeline image from this repository, inside the account
#   network   a VPC with public subnets for the pipeline's tasks (no NAT)
#   pipeline  the sweep task, triggered by uploads and on a schedule
#   identity  Cognito sign-in for the portal
#   portal    CloudFront, the static page and its API
#
# After apply: upload files to s3://<lake>/landing/<collection>/ (outputs.upload_to) and open the portal.

locals {
  repo_root     = abspath("${path.module}/../../..")
  private_group = "private-readers"

  # Each collection's config, with the defaults filled in: uploads under landing/<id>/, a
  # profile named after the collection, and an ontology namespace of its own.
  collections = { for id, c in var.collections : id => {
    sources = c.sources != null ? c.sources : [
      { name = "uploads", type = "s3_landing", options = { prefix = "landing/${id}/" }, scope = "public" }
    ]
    profile = {
      name              = coalesce(c.profile.name, title(replace(id, "-", " ")))
      description       = c.profile.description
      key_terms         = c.profile.key_terms
      example_questions = c.profile.example_questions
      ontology_base     = coalesce(c.profile.ontology_base, "https://example.org/${var.name}/${id}/ontology#")
    }
    settings = {
      ontology_mode            = c.ontology_mode
      discovery_min_docs       = var.discovery.min_docs
      discovery_sample         = var.discovery.sample
      discovery_resamples      = var.discovery.resamples
      discovery_target_classes = var.discovery.target_classes
      extraction_workers       = var.extraction_workers
    }
  } }

  # Buckets outside the lake that sources read, from their options: granted to the pipeline.
  source_buckets = distinct(compact(flatten([for c in local.collections : [
    for s in c.sources : try(s.options.bucket, "")
  ]])))
}

module "lake" {
  source        = "../lake"
  name          = var.name
  collections   = local.collections
  force_destroy = var.force_destroy_lake
}

module "build" {
  source      = "../image-build"
  name        = var.name
  source_dir  = local.repo_root
  build_agent = var.agent.enabled
}

module "network" {
  source = "../network"
  name   = var.name
}

module "pipeline" {
  source                       = "../pipeline"
  name                         = var.name
  image_uri                    = module.build.image_uri
  lake_bucket                  = module.lake.bucket
  lake_bucket_arn              = module.lake.bucket_arn
  extra_read_bucket_arns       = [for b in local.source_buckets : "arn:aws:s3:::${b}"]
  vpc_id                       = module.network.vpc_id
  subnet_ids                   = module.network.public_subnet_ids
  llm_provider                 = var.llm_provider
  anthropic_api_key_secret_arn = var.anthropic_api_key_secret_arn
  extraction_model_id          = var.extraction_model_id
  schedule_expression          = var.schedule_expression
  schedule_enabled             = var.schedule_enabled
}

module "identity" {
  source        = "../identity"
  name          = var.name
  admin_email   = var.admin_email
  groups        = [local.private_group]
  admin_groups  = var.admin_private ? [local.private_group] : []
  callback_urls = [module.portal.url]
  # With the agent: the agent's own identity (public tools only), and one application client for
  # callers of the agent. Give callers private scope with agent.caller_private.
  machine_clients = var.agent.enabled ? {
    agent  = { scopes = ["tools.public"] }
    caller = { scopes = concat(["agent.invoke", "tools.public"], var.agent.caller_private ? ["tools.private"] : []) }
  } : {}
}

module "portal" {
  source                       = "../portal"
  name                         = var.name
  package_root                 = "${local.repo_root}/src"
  portal_dir                   = "${local.repo_root}/portal"
  lake_bucket                  = module.lake.bucket
  lake_bucket_arn              = module.lake.bucket_arn
  cognito_issuer               = module.identity.issuer
  cognito_client_id            = module.identity.client_id
  cognito_domain_url           = module.identity.domain_url
  private_group                = local.private_group
  llm_provider                 = var.llm_provider
  anthropic_api_key_secret_arn = var.anthropic_api_key_secret_arn
  chat_model_id                = var.chat_model_id
  daily_questions              = var.daily_questions
  brand_name                   = var.portal_title
}

module "agent" {
  count               = var.agent.enabled ? 1 : 0
  source              = "../agent"
  name                = var.name
  package_root        = "${local.repo_root}/src"
  tool_schema_path    = "${local.repo_root}/src/knowledge_store/tools/schema.json"
  lake_bucket         = module.lake.bucket
  lake_bucket_arn     = module.lake.bucket_arn
  discovery_url       = module.identity.discovery_url
  allowed_client_ids  = concat([module.identity.client_id], values(module.identity.machine_client_ids))
  agent_client_id     = module.identity.machine_client_ids["agent"]
  agent_client_secret = module.identity.machine_client_secrets["agent"]
  scope_prefix        = module.identity.scope_prefix
  private_group       = local.private_group
  agent_image_uri     = module.build.agent_image_uri
  runtime_enabled     = var.agent.runtime
  prod_version        = var.agent.prod_version
  agent_model_id      = var.agent.model_id
  judge_model_id      = var.agent.judge_model_id
  policy_mode         = var.agent.policy_mode
  browser_enabled     = var.agent.browser
  transaction_search  = var.agent.transaction_search
  evaluations_enabled = var.agent.evaluations
  registry_enabled    = var.agent.registry
  harness_enabled     = var.agent.harness
}
