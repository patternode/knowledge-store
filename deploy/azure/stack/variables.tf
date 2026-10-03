# The reference root's inputs, passed to the module unchanged. See
# ../modules/knowledge-store/variables.tf for what each one does.

variable "subscription_id" {
  type        = string
  description = "the subscription to deploy into; the provider refuses to guess"
}
variable "name" {
  type    = string
  default = "knowledge-store"
}
variable "location" {
  type    = string
  default = "eastus2"
}
variable "admin_principal_ids" {
  type = list(string)
}
variable "publisher_email" {
  type = string
}
variable "tags" {
  type    = map(string)
  default = {}
}
variable "collections" {
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
  type    = string
  default = "0 */6 * * *"
}
variable "schedule_enabled" {
  type    = bool
  default = true
}
variable "foundry" {
  type = object({
    resource_name       = string
    resource_group_name = string
    extraction_model    = optional(string, "claude-sonnet-5")
    chat_model          = optional(string, "claude-sonnet-5")
  })
}
variable "profile" {
  type    = string
  default = "native"
}
variable "graph" {
  type    = bool
  default = false
}
variable "document_projection" {
  type    = bool
  default = false
}
variable "mongodb_uri" {
  type      = string
  default   = ""
  sensitive = true
}
variable "neo4j" {
  type = object({
    uri      = string
    username = optional(string, "neo4j")
    database = optional(string, "neo4j")
  })
  default = null
}
variable "neo4j_password" {
  type      = string
  default   = ""
  sensitive = true
}
variable "portal_title" {
  type    = string
  default = "Knowledge Store"
}
variable "daily_questions" {
  type    = number
  default = 30
}
variable "apim_sku" {
  type    = string
  default = "BasicV2_1"
}
variable "mcp_calls_per_minute" {
  type    = number
  default = 120
}
variable "copilot_redirect_uris" {
  type    = list(string)
  default = ["https://global.consent.azure-apim.net/redirect"]
}
variable "force_destroy_lake" {
  type    = bool
  default = false
}
variable "python_command" {
  type    = string
  default = "python"
}
