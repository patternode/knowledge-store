# The Knowledge Store module: everything, in one apply. A root calls it with its own provider
# and backend: infra/stack is the reference root, examples/deployment a template for your own.
#
# Ingestion: documents in, an ontology applied (provided, or discovered and reviewed), a knowledge graph out.
#   lake             the bucket, layered by prefix, with the deployer's sources, profile and settings
#   build            CodeBuild builds the pipeline and agent images from this repository, inside the account
#   network          a VPC: public subnets for the pipeline's tasks, private ones for Neptune (no NAT);
#                    or the VPC and subnets you bring (network.existing)
#   pipeline         the sweep task, triggered by uploads and on a schedule
#   knowledge_graph  Neptune, holding the gold RDF; the sweep loads it
#   knowledge_base   the passages' vector index (Bedrock Knowledge Base on S3 Vectors); the sweep syncs it
#
# Chat: a person asks, an agent answers from the graph, every statement linked to its source.
#   identity         Cognito sign-in
#   portal           CloudFront, the chat page and its API (a quota per person, a concurrency cap)
#   agent            the chat agent on AgentCore Runtime, its tools behind AgentCore Gateway, a guardrail
#
# After the first apply: upload files to s3://<lake>/landing/<collection>/ (outputs.upload_to);
# once the agent image is built, set agent.runtime = true and apply again; open the portal.

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
      discovery_review         = var.discovery.review
      extraction_workers       = var.extraction_workers
    }
  } }

  # Provided ontologies: "<collection>/<file>" => local path, for the lake's config/ontology/.
  ontology_files = merge([for id, c in var.collections : {
    for f in ["ontology.ttl", "shapes.ttl"] : "${id}/${f}" => abspath("${c.ontology_dir}/${f}")
    if fileexists("${c.ontology_dir}/${f}")
  } if c.ontology_dir != null]...)

  # The network: the module's own VPC, or one you bring (network.existing).
  own_network        = var.network.existing == null
  vpc_id             = local.own_network ? module.network[0].vpc_id : var.network.existing.vpc_id
  private_subnet_ids = local.own_network ? module.network[0].private_subnet_ids : var.network.existing.private_subnet_ids
  # The pipeline's tasks need Bedrock (or the Anthropic API), ECR and S3: from public subnets with a
  # public IP, or from private subnets behind a NAT gateway.
  pipeline_subnet_ids = (local.own_network
    ? (var.network.enable_nat ? module.network[0].private_subnet_ids : module.network[0].public_subnet_ids)
  : var.network.existing.pipeline_subnet_ids)
  pipeline_public_ip = local.own_network ? !var.network.enable_nat : var.network.existing.pipeline_public_ip

  # Buckets outside the lake that sources read, from their options: granted to the pipeline.
  source_buckets = distinct(compact(flatten([for c in local.collections : [
    for s in c.sources : try(s.options.bucket, "")
  ]])))
}

# Every log group's retention, and every IAM role's permissions boundary.
locals {
  logs     = var.log_retention_days
  boundary = var.permissions_boundary
}

module "lake" {
  source         = "../lake"
  name           = var.name
  collections    = local.collections
  ontology_files = local.ontology_files
  force_destroy  = var.force_destroy_lake
}

module "build" {
  source               = "../image-build"
  name                 = var.name
  source_dir           = local.repo_root
  build_agent          = true
  permissions_boundary = local.boundary
}

module "network" {
  count      = local.own_network ? 1 : 0
  source     = "../network"
  name       = var.name
  cidr       = var.network.cidr
  az_count   = var.network.az_count
  enable_nat = var.network.enable_nat
}

moved {
  from = module.network
  to   = module.network[0]
}

module "knowledge_graph" {
  count                     = var.knowledge_graph.enabled ? 1 : 0
  source                    = "../knowledge-graph"
  name                      = var.name
  vpc_id                    = local.vpc_id
  private_subnet_ids        = local.private_subnet_ids
  client_security_group_ids = { pipeline = module.pipeline.security_group_id }
  instance_class            = var.knowledge_graph.instance_class
  serverless_min_ncu        = var.knowledge_graph.serverless_min_ncu
  serverless_max_ncu        = var.knowledge_graph.serverless_max_ncu
  deletion_protection       = var.knowledge_graph.deletion_protection
}

module "knowledge_base" {
  count                = var.knowledge_base.enabled ? 1 : 0
  source               = "../knowledge-base"
  name                 = var.name
  lake_bucket_arn      = module.lake.bucket_arn
  embedding_model_id   = var.knowledge_base.embedding_model_id
  permissions_boundary = local.boundary
}

locals {
  neptune = var.knowledge_graph.enabled ? {
    endpoint = module.knowledge_graph[0].endpoint
    port     = module.knowledge_graph[0].port
    data_arn = module.knowledge_graph[0].data_arn
  } : null
  knowledge_base = var.knowledge_base.enabled ? {
    id             = module.knowledge_base[0].knowledge_base_id
    arn            = module.knowledge_base[0].knowledge_base_arn
    data_source_id = module.knowledge_base[0].data_source_id
  } : null
}

module "pipeline" {
  source                       = "../pipeline"
  name                         = var.name
  image_uri                    = module.build.image_uri
  lake_bucket                  = module.lake.bucket
  lake_bucket_arn              = module.lake.bucket_arn
  extra_read_bucket_arns       = [for b in local.source_buckets : "arn:aws:s3:::${b}"]
  vpc_id                       = local.vpc_id
  subnet_ids                   = local.pipeline_subnet_ids
  assign_public_ip             = local.pipeline_public_ip
  log_retention_days           = local.logs
  permissions_boundary         = local.boundary
  llm_provider                 = var.llm_provider
  anthropic_api_key_secret_arn = var.anthropic_api_key_secret_arn
  extraction_model_id          = var.extraction_model_id
  schedule_expression          = var.schedule_expression
  schedule_enabled             = var.schedule_enabled
  neptune                      = local.neptune
  knowledge_base               = local.knowledge_base
}

module "identity" {
  source        = "../identity"
  name          = var.name
  admin_email   = var.admin_email
  groups        = [local.private_group]
  admin_groups  = var.admin_private ? [local.private_group] : []
  callback_urls = distinct([module.portal.url, module.portal.cloudfront_url])
}

module "portal" {
  source                       = "../portal"
  name                         = var.name
  package_root                 = "${local.repo_root}/src"
  portal_dir                   = "${local.repo_root}/chat"
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
  reserved_concurrency         = var.valves.chat_concurrency
  brand_name                   = var.portal_title
  agent_runtime_arn            = module.agent.runtime_arn
  agent_runtime_qualifier      = module.agent.runtime_qualifier
  domain_name                  = var.portal_domain.name
  certificate_arn              = var.portal_domain.certificate_arn
  log_retention_days           = local.logs
  permissions_boundary         = local.boundary
}

module "agent" {
  source             = "../agent"
  name               = var.name
  package_root       = "${local.repo_root}/src"
  tool_schema_dir    = "${local.repo_root}/src/knowledge_store/tools"
  lake_bucket        = module.lake.bucket
  lake_bucket_arn    = module.lake.bucket_arn
  discovery_url      = module.identity.discovery_url
  allowed_client_ids = [module.identity.client_id]
  scope_prefix       = module.identity.scope_prefix
  private_group      = local.private_group
  agent_image_uri    = module.build.agent_image_uri
  runtime_enabled    = var.agent.runtime
  prod_version       = var.agent.prod_version
  agent_model_id     = var.agent.model_id
  neptune = var.knowledge_graph.enabled ? {
    endpoint                 = module.knowledge_graph[0].endpoint
    port                     = module.knowledge_graph[0].port
    data_arn                 = module.knowledge_graph[0].data_arn
    client_security_group_id = module.knowledge_graph[0].client_security_group_id
    private_subnet_ids       = local.private_subnet_ids
  } : null
  knowledge_base = var.knowledge_base.enabled ? { id = local.knowledge_base.id, arn = local.knowledge_base.arn } : null
  guardrail      = var.guardrail
  valves = {
    max_tool_calls    = var.valves.max_tool_calls
    max_model_calls   = var.valves.max_model_calls
    max_output_tokens = var.valves.max_output_tokens
    grounding_repairs = var.valves.grounding_repairs
  }
  log_retention_days   = local.logs
  permissions_boundary = local.boundary
}

moved {
  from = module.agent[0]
  to   = module.agent
}

# A monthly cost budget for the whole account, mailed at 80% of actual and 100% of forecast spend.
resource "aws_budgets_budget" "monthly" {
  count        = var.budget.monthly_usd > 0 ? 1 : 0
  name         = "${var.name}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.budget.monthly_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [coalesce(var.budget.email, var.admin_email)]
  }
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [coalesce(var.budget.email, var.admin_email)]
  }
}
