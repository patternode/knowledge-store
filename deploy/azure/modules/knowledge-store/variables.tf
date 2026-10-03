# The Knowledge Store module for Azure. Required: admin_principal_ids, publisher_email and the
# Foundry resource. Everything else has a default that works. Where it deploys (subscription,
# tenant, credentials) is the caller's provider configuration; see deploy/azure/stack.

variable "name" {
  type        = string
  default     = "knowledge-store"
  description = "prefix for every resource; globally unique names add a short random suffix"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,19}$", var.name))
    error_message = "name must be 3-20 characters (Container Apps job names are capped at 32): lower case letters, digits and hyphens, starting with a letter."
  }
}

variable "location" {
  type        = string
  default     = "eastus2"
  description = "the Azure region for everything the module creates"
}

variable "admin_principal_ids" {
  type        = list(string)
  description = <<-EOT
    Entra object ids of the people (or groups) who curate: they get the private-reader role in the
    portal and may upload to the lake. Assigning an app role to a group needs Entra ID P1; users
    work on every tenant.
  EOT
  validation {
    condition     = length(var.admin_principal_ids) > 0
    error_message = "name at least one admin principal."
  }
}

variable "publisher_email" {
  type        = string
  description = "API Management's publisher contact (it sends service notices there)"
}

variable "tags" {
  type    = map(string)
  default = {}
}

# --- what (optional) -------------------------------------------------------------------------

variable "collections" {
  description = <<-EOT
    The corpora, each with its own ontology, as in the AWS module. Keys are collection ids. Per
    collection, all optional: profile {name, description, key_terms, example_questions,
    ontology_base}, sources (default: uploads under landing/<id>/ in the lake), ontology_mode
    (curated or auto).
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
  }))
  default = { default = {} }
  validation {
    condition     = alltrue([for k, v in var.collections : can(regex("^[a-z0-9][a-z0-9-]{0,39}$", k)) && contains(["curated", "auto"], v.ontology_mode)])
    error_message = "collection ids are 1-40 lower case letters, digits and hyphens; ontology_mode is curated or auto."
  }
}

variable "discovery" {
  type = object({
    min_docs       = optional(number, 5)
    sample         = optional(number, 20)
    resamples      = optional(number, 2)
    target_classes = optional(number, 15)
  })
  default = {}
}
variable "extraction_workers" {
  type    = number
  default = 4
}
variable "schedule_cron" {
  type        = string
  default     = "0 */6 * * *"
  description = "when the safety-net sweep runs (UTC, cron)"
}
variable "schedule_enabled" {
  type    = bool
  default = true
}

# --- models ------------------------------------------------------------------------------------

variable "foundry" {
  type = object({
    resource_name       = string
    resource_group_name = string
    extraction_model    = optional(string, "claude-sonnet-5")
    chat_model          = optional(string, "claude-sonnet-5")
  })
  description = <<-EOT
    The Microsoft Foundry resource with the Claude deployments (created beforehand, because
    deploying Claude accepts Anthropic's marketplace terms). The models are deployment names.
  EOT
}

# --- profile and backends ------------------------------------------------------------------------

variable "profile" {
  type        = string
  default     = "native"
  description = <<-EOT
    native: Cosmos DB for MongoDB (serverless) and, with graph = true, PostgreSQL with Apache AGE.
    common: your MongoDB (mongodb_uri, e.g. Atlas) and, with graph = true, your Neo4j (neo4j).
  EOT
  validation {
    condition     = contains(["native", "common"], var.profile)
    error_message = "profile is native or common."
  }
}
variable "graph" {
  type        = bool
  default     = false
  description = "load the projection into a graph database (AGE or Neo4j, by profile) for traversals"
}
variable "document_projection" {
  type        = bool
  default     = false
  description = "serve the portal's projection from MongoDB instead of each instance's memory"
}
variable "mongodb_uri" {
  type        = string
  default     = ""
  sensitive   = true
  description = "profile common: the MongoDB connection string (Atlas: mongodb+srv://...)"
  validation {
    condition     = var.profile == "native" || var.mongodb_uri != ""
    error_message = "profile common needs mongodb_uri."
  }
}
variable "neo4j" {
  type = object({
    uri      = string
    username = optional(string, "neo4j")
    database = optional(string, "neo4j")
  })
  default     = null
  description = "profile common with graph = true: the Neo4j instance (AuraDB: neo4j+s://<id>.databases.neo4j.io)"
  validation {
    condition     = !(var.profile == "common" && var.graph) || var.neo4j != null
    error_message = "profile common with graph = true needs neo4j."
  }
}
variable "neo4j_password" {
  type      = string
  default   = ""
  sensitive = true
  validation {
    condition     = !(var.profile == "common" && var.graph) || var.neo4j_password != ""
    error_message = "profile common with graph = true needs neo4j_password."
  }
}

# --- portal, gateway, agents -------------------------------------------------------------------

variable "portal_title" {
  type    = string
  default = "Knowledge Store"
}
variable "daily_questions" {
  type    = number
  default = 30
}
variable "apim_sku" {
  type        = string
  default     = "BasicV2_1"
  description = "API Management tier for the MCP gateway (v2 tiers deploy in minutes and support rate-limit-by-key)"
}
variable "mcp_calls_per_minute" {
  type    = number
  default = 120
}
variable "copilot_redirect_uris" {
  type        = list(string)
  default     = ["https://global.consent.azure-apim.net/redirect"]
  description = "the OAuth redirect URIs of the Copilot Studio connector; add the connector's own one after creating it"
}
variable "force_destroy_lake" {
  type    = bool
  default = false
}
variable "python_command" {
  type        = string
  default     = "python"
  description = "the Python 3.12+ that packages the Function App where Terraform runs (python3 on some systems)"
}
