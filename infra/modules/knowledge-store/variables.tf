# The Knowledge Store module. Only admin_email is required. Everything else has a default that
# works; names and bucket locations are derived from `name` and the account, and each
# collection's uploads go under landing/<collection id>/ in the lake unless its sources say
# otherwise. Where it deploys (region, account, credentials, tags) is the caller's provider.

variable "admin_email" {
  type        = string
  description = "the first portal user; Cognito emails them a temporary password"
}

variable "name" {
  type        = string
  default     = "knowledge-store"
  description = "prefix for every resource; buckets are <name>-lake-<account>, <name>-site-<account>, ..."
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,24}$", var.name))
    error_message = "name must be 3-25 characters: lower case letters, digits and hyphens, starting with a letter."
  }
}

# --- what (optional) -------------------------------------------------------------------------

variable "collections" {
  description = <<-EOT
    The corpora, each with its own ontology. Keys are collection ids (lower case, digits,
    hyphens). Per collection, all optional:
      profile  what the collection is about: {name, description, key_terms, example_questions,
               ontology_base}. It guides prompts and the portal; it is not the ontology.
      sources  where content comes from. Default: [{name = "uploads", type = "s3_landing",
               options = {prefix = "landing/<id>/"}}]. An s3_landing source with
               options.bucket reads another bucket; the pipeline is granted read access to it.
      ontology_mode  curated (a person publishes each version; the default) or auto.
      ontology_dir   bring your own ontology instead of discovering one: a directory, relative
                     to where you run Terraform, holding ontology.ttl (OWL, with owl:versionInfo
                     set to its version) and optionally shapes.ttl. The sweep publishes and
                     activates it; to change it, edit it, bump owl:versionInfo and apply.
  EOT
  type = map(object({
    profile = optional(object({
      name              = optional(string)
      description       = optional(string, "")
      key_terms         = optional(list(string), [])
      example_questions = optional(list(string), [])
      ontology_base     = optional(string)
    }), {})
    sources = optional(list(object({
      name    = string
      type    = string
      options = optional(map(any), {})
      scope   = optional(string, "public")
    })))
    ontology_mode = optional(string, "curated")
    ontology_dir  = optional(string)
  }))
  default = { default = {} }
  validation {
    condition     = alltrue([for k, v in var.collections : can(regex("^[a-z0-9][a-z0-9-]{0,39}$", k)) && contains(["curated", "auto"], v.ontology_mode)])
    error_message = "collection ids are 1-40 lower case letters, digits and hyphens; ontology_mode is curated or auto."
  }
  validation {
    condition     = alltrue([for k, v in var.collections : v.ontology_dir == null || fileexists("${coalesce(v.ontology_dir, ".")}/ontology.ttl")])
    error_message = "an ontology_dir must hold ontology.ttl."
  }
}

variable "discovery" {
  type = object({
    min_docs       = optional(number, 5)
    sample         = optional(number, 20)
    resamples      = optional(number, 2)
    target_classes = optional(number, 15)
    review         = optional(bool, true) # a second model pass that fixes the draft's hierarchy, duplicates and domains
  })
  default = {}
}
variable "extraction_workers" {
  type    = number
  default = 4
}
variable "schedule_expression" {
  type    = string
  default = "rate(6 hours)"
}
variable "schedule_enabled" {
  type    = bool
  default = true
}

# --- models (optional) -------------------------------------------------------------------------

variable "llm_provider" {
  type        = string
  default     = "bedrock"
  description = "bedrock keeps every model call inside AWS; anthropic sends them to the Anthropic API"
  validation {
    condition     = contains(["bedrock", "anthropic"], var.llm_provider)
    error_message = "llm_provider must be bedrock or anthropic."
  }
}
variable "anthropic_api_key_secret_arn" {
  type        = string
  default     = ""
  description = "with llm_provider = anthropic: a Secrets Manager secret holding the API key"
}
variable "extraction_model_id" {
  type    = string
  default = "us.anthropic.claude-sonnet-5"
}
variable "chat_model_id" {
  type    = string
  default = "us.anthropic.claude-sonnet-5"
}

# --- portal (optional) -------------------------------------------------------------------------

variable "portal_title" {
  type        = string
  default     = "Knowledge Store"
  description = "the name in the portal's header"
}
variable "admin_private" {
  type        = bool
  default     = true
  description = "put the admin user in the private-readers group"
}
variable "daily_questions" {
  type    = number
  default = 30
}
variable "force_destroy_lake" {
  type    = bool
  default = false
}

# --- the knowledge graph and the passages' index ------------------------------------------------

variable "knowledge_graph" {
  description = <<-EOT
    Neptune, holding the gold RDF, which the agent's graph tools query. On by default; it is the
    stack's main fixed cost (db.t3.medium runs about 60 USD a month). enabled = false answers the
    graph tools from the lake's projection in memory instead, which suits a small demo.
    serverless_min_ncu > 0 uses Neptune Serverless.
  EOT
  type = object({
    enabled             = optional(bool, true)
    instance_class      = optional(string, "db.t3.medium")
    serverless_min_ncu  = optional(number, 0)
    serverless_max_ncu  = optional(number, 8)
    deletion_protection = optional(bool, false)
  })
  default = {}
}

variable "knowledge_base" {
  description = <<-EOT
    Search of the passages by meaning: a Bedrock Knowledge Base on S3 Vectors (cents a month at
    rest). On by default; needs the embedding model enabled in Bedrock. enabled = false searches
    passages by keyword instead.
  EOT
  type = object({
    enabled            = optional(bool, true)
    embedding_model_id = optional(string, "amazon.titan-embed-text-v2:0")
  })
  default = {}
}

# --- the chat agent -----------------------------------------------------------------------------

variable "agent" {
  description = <<-EOT
    The chat agent on AgentCore Runtime. Two applies: the first builds its image (CodeBuild) and
    creates its Gateway, tools and guardrail; once the image is in ECR, set runtime = true and
    apply again. Until then the portal answers with its own tool loop. prod_version pins a tested
    Runtime version as the prod endpoint the portal calls.
  EOT
  type = object({
    runtime      = optional(bool, false)
    prod_version = optional(string, "")
    model_id     = optional(string, "us.anthropic.claude-sonnet-5")
  })
  default = {}
}

variable "guardrail" {
  description = "a Bedrock Guardrail: screens each question, and checks each claim against the passages it cites"
  type = object({
    enabled             = optional(bool, true)
    grounding_threshold = optional(number, 0.75)
  })
  default = {}
}

variable "valves" {
  description = <<-EOT
    Limits around every question (daily_questions per person is a variable of its own):
      max_tool_calls, max_model_calls, max_output_tokens   per question, in the agent
      grounding_repairs   times the agent is shown its failed citations and asked again
      chat_concurrency    the chat API's reserved concurrency (-1 none, 0 turns the chat off)
  EOT
  type = object({
    max_tool_calls    = optional(number, 16)
    max_model_calls   = optional(number, 14)
    max_output_tokens = optional(number, 4000)
    grounding_repairs = optional(number, 1)
    chat_concurrency  = optional(number, 20)
  })
  default = {}
}

variable "budget" {
  description = "a monthly cost budget for the account, mailed to email (default admin_email); 0 for none"
  type = object({
    monthly_usd = optional(number, 0)
    email       = optional(string)
  })
  default = {}
}

# --- where it runs in your AWS estate (all optional) --------------------------------------------

variable "network" {
  description = <<-EOT
    The network. By default the module creates its own VPC: public subnets for the pipeline's
    tasks, private subnets with no route out for Neptune and the graph tools, and an S3 gateway
    endpoint. Options:
      cidr, az_count  the VPC's range and how many availability zones it spans
      enable_nat      a NAT gateway (about 33 USD a month), and the pipeline's tasks in the
                      private subnets with no public IP
      existing        use a VPC you already have instead of creating one:
        vpc_id               the VPC
        private_subnet_ids   two or more subnets in different zones for Neptune and the graph tools;
                             they must reach S3 (a gateway endpoint on their route table, or a NAT)
        pipeline_subnet_ids  subnets for the pipeline's tasks, which must reach Bedrock (or the
                             Anthropic API), ECR and S3
        pipeline_public_ip   true for public subnets (a public IP, through an internet gateway);
                             false for private subnets with a NAT or the VPC endpoints they need
  EOT
  type = object({
    cidr       = optional(string, "10.42.0.0/16")
    az_count   = optional(number, 2)
    enable_nat = optional(bool, false)
    existing = optional(object({
      vpc_id              = string
      private_subnet_ids  = list(string)
      pipeline_subnet_ids = list(string)
      pipeline_public_ip  = optional(bool, false)
    }))
  })
  default = {}
  validation {
    condition     = can(cidrhost(var.network.cidr, 0)) && var.network.az_count >= 2 && var.network.az_count <= 6
    error_message = "network.cidr must be a CIDR block, and network.az_count 2 to 6 (Neptune needs subnets in two zones)."
  }
  validation {
    condition = var.network.existing == null || try(
      length(var.network.existing.private_subnet_ids) >= 2 && length(var.network.existing.pipeline_subnet_ids) >= 1,
    false)
    error_message = "network.existing needs at least two private_subnet_ids (in different zones) and one pipeline_subnet_ids."
  }
}

variable "portal_domain" {
  description = <<-EOT
    Serve the portal on a domain of your own (portal.example.org) instead of CloudFront's. Needs an
    ACM certificate for it in us-east-1, which CloudFront requires whatever the stack's region.
    After apply, point a CNAME (or a Route 53 alias) for the name at the portal_cloudfront_domain
    output. Sign-in accepts both the custom URL and CloudFront's.
  EOT
  type = object({
    name            = optional(string, "")
    certificate_arn = optional(string, "")
  })
  default = {}
  validation {
    condition     = (var.portal_domain.name == "") == (var.portal_domain.certificate_arn == "")
    error_message = "portal_domain needs both name and certificate_arn, or neither."
  }
  validation {
    condition     = var.portal_domain.certificate_arn == "" || startswith(var.portal_domain.certificate_arn, "arn:aws:acm:us-east-1:")
    error_message = "portal_domain.certificate_arn must be an ACM certificate in us-east-1 (CloudFront's requirement)."
  }
}

variable "permissions_boundary" {
  type        = string
  default     = null
  description = "an IAM policy ARN set as the permissions boundary of every role the module creates, where your organisation requires one"
}

variable "log_retention_days" {
  type        = number
  default     = 30
  description = "how long the pipeline's, the chat API's and the tools' CloudWatch logs are kept"
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.log_retention_days)
    error_message = "log_retention_days must be a value CloudWatch Logs accepts (1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, ...)."
  }
}
