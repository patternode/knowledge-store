# The Knowledge Store on Azure: everything, in one apply. A root calls it with its own provider
# and backend: deploy/azure/stack is the reference root.
#
#   main.tf      naming, the resource group, identities, monitoring, Key Vault
#   entra.tf     app registrations: the API, the portal, the Copilot Studio connector
#   lake.tf      the lake, its upload notifications, the collections' config
#   pipeline.tf  the image (ACR Tasks) and the sweep (Container Apps jobs)
#   backends.tf  MongoDB (Cosmos DB or yours) and the graph (AGE or your Neo4j)
#   api.tf       the Function App: portal API, MCP tools, chat worker
#   gateway.tf   API Management in front of the MCP tools
#   site.tf      the portal page (a static website)
#
# Every service authenticates to every other with a managed identity; storage account keys are off.
# See docs/architectures/azure.md for the design and docs/architectures/azure-setup.md to deploy.

data "azurerm_client_config" "me" {}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

locals {
  repo_root = abspath("${path.module}/../../../..")
  tenant_id = data.azurerm_client_config.me.tenant_id
  # Storage accounts, registries and vaults need globally unique, short, alphanumeric names.
  short = "${substr(replace(var.name, "-", ""), 0, 12)}${random_string.suffix.result}"
  tags  = merge({ project = var.name, managed-by = "terraform", stack = "knowledge-store" }, var.tags)

  graph_backend = var.graph ? (var.profile == "native" ? "age" : "neo4j") : "none"

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
}

resource "azurerm_resource_group" "this" {
  name     = "rg-${var.name}"
  location = var.location
  tags     = local.tags
}

# --- identities: one per workload, each granted only what it uses ------------------------------

resource "azurerm_user_assigned_identity" "this" {
  for_each            = toset(["pipeline", "api", "events"])
  name                = "id-${var.name}-${each.key}"
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.tags
}

locals {
  id = { for k, v in azurerm_user_assigned_identity.this : k => v }
}

# --- monitoring ---------------------------------------------------------------------------------

resource "azurerm_log_analytics_workspace" "this" {
  name                = "log-${var.name}"
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

resource "azurerm_application_insights" "this" {
  name                = "appi-${var.name}"
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  workspace_id        = azurerm_log_analytics_workspace.this.id
  application_type    = "other"
  tags                = local.tags
}

# --- Key Vault: the few secrets that exist (MongoDB and Neo4j credentials) ------------------------

resource "azurerm_key_vault" "this" {
  name                       = "kv-${local.short}"
  location                   = var.location
  resource_group_name        = azurerm_resource_group.this.name
  tenant_id                  = local.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  soft_delete_retention_days = 7
  purge_protection_enabled   = false
  tags                       = local.tags
}

# The deployer writes secrets and the lake's config objects; the data plane needs roles for that,
# and new role assignments take a minute to apply.
resource "azurerm_role_assignment" "deployer" {
  for_each = {
    kv   = { scope = azurerm_key_vault.this.id, role = "Key Vault Secrets Officer" }
    lake = { scope = azurerm_storage_account.lake.id, role = "Storage Blob Data Contributor" }
    site = { scope = azurerm_storage_account.site.id, role = "Storage Blob Data Contributor" }
  }
  scope                = each.value.scope
  role_definition_name = each.value.role
  principal_id         = data.azurerm_client_config.me.object_id
}

resource "time_sleep" "deployer_roles" {
  depends_on      = [azurerm_role_assignment.deployer]
  create_duration = "90s"
}

# The Foundry resource with the Claude deployments, created beforehand.
data "azurerm_cognitive_account" "foundry" {
  name                = var.foundry.resource_name
  resource_group_name = var.foundry.resource_group_name
}

resource "azurerm_role_assignment" "foundry" {
  for_each             = toset(["pipeline", "api"])
  scope                = data.azurerm_cognitive_account.foundry.id
  role_definition_name = "Cognitive Services User"
  principal_id         = local.id[each.key].principal_id
}

resource "azurerm_role_assignment" "secrets" {
  for_each = {
    pipeline = local.id["pipeline"].principal_id
    api      = azurerm_function_app_flex_consumption.api.identity[0].principal_id # Key Vault references resolve as the app
  }
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = each.value
}

locals {
  # The environment the pipeline and the API share: where the lake is, which model, which backends,
  # and how to read an Entra token's claims (knowledge_store.claims).
  common_env = merge({
    LLM_PROVIDER               = "foundry"
    ANTHROPIC_FOUNDRY_RESOURCE = coalesce(data.azurerm_cognitive_account.foundry.custom_subdomain_name, var.foundry.resource_name)
    LAKE_URI                   = "az://${azurerm_storage_account.lake.name}/${azurerm_storage_container.lake.name}"
    GRAPH_BACKEND              = local.graph_backend
    PROJECTION_STORE           = var.document_projection ? "mongodb" : "memory"
    CHAT_STATE                 = "mongodb"
    MONGODB_DB                 = "knowledge_store"
    SUBJECT_CLAIM              = "oid,sub"
    GROUPS_CLAIM               = "roles"
    PRIVATE_GROUP              = "private-reader"
    SCOPES_CLAIM               = "roles"
    PRIVATE_SCOPE              = "tools.private"
    }, local.graph_backend == "age" ? {
    AGE_ENTRA = "1"
    AGE_LOAD  = "0"
    } : {}, local.graph_backend == "neo4j" ? {
    NEO4J_URI      = var.neo4j.uri
    NEO4J_USERNAME = var.neo4j.username
    NEO4J_DATABASE = var.neo4j.database
  } : {})
}
