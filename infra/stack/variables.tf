# Only admin_email is required. Everything else has a default that works; names and bucket
# locations are derived from `name` and the account, and each collection's uploads go under
# landing/<collection id>/ in the lake unless its sources say otherwise.

variable "admin_email" {
  type        = string
  description = "the first portal user; Cognito emails them a temporary password"
}

# --- where (all optional) ------------------------------------------------------------------

variable "region" {
  type    = string
  default = "us-east-1"
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
variable "account_id" {
  type        = string
  default     = ""
  description = "optional guard: when set, the provider refuses to apply to any other account"
}
variable "aws_profile" {
  type        = string
  default     = ""
  description = "a named AWS CLI profile, or empty to use the environment's credentials"
}
variable "extra_tags" {
  type    = map(string)
  default = {}
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

# --- the example agent (AgentCore), optional ------------------------------------------------------

variable "agent" {
  description = <<-EOT
    The example task agent and the AgentCore services it uses. Off by default. Two applies: first
    with enabled = true (builds the agent image, creates Gateway, Memory, Identity and tools), then,
    once the image is in ECR, with runtime = true. Account-wide switches are separate and off by
    default because they change the whole account: transaction_search (spans to CloudWatch, needed
    by evaluations).
  EOT
  type = object({
    enabled            = optional(bool, false)
    runtime            = optional(bool, false)
    prod_version       = optional(string, "")
    caller_private     = optional(bool, false)
    policy_mode        = optional(string, "ENFORCE")
    browser            = optional(bool, false)
    transaction_search = optional(bool, false)
    evaluations        = optional(bool, false)
    registry           = optional(bool, false)
    harness            = optional(bool, false)
    model_id           = optional(string, "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
    judge_model_id     = optional(string, "us.anthropic.claude-haiku-4-5-20251001-v1:0")
  })
  default = {}
}
