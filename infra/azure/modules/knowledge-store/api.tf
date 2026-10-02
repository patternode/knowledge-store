# The Function App (Flex Consumption: scales to zero, per-execution billing): the portal API,
# the knowledge tools over MCP, and the chat worker. The code is functions/azure with the
# package and its Linux wheels, zipped by infra/azure/package_function.py and deployed by
# Terraform. Every HTTP route verifies the caller's Entra token itself (knowledge_store.authn).

resource "azurerm_storage_account" "func" {
  name                            = "st${local.short}fn"
  location                        = var.location
  resource_group_name             = azurerm_resource_group.this.name
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true
  allow_nested_items_to_be_public = false
  tags                            = local.tags
}

resource "azurerm_storage_container" "deployments" {
  name               = "deployments"
  storage_account_id = azurerm_storage_account.func.id
}

# The Functions host keeps its leases, timers and queue bookkeeping here, as the app's identity.
resource "azurerm_role_assignment" "func_host" {
  for_each             = toset(["Storage Blob Data Owner", "Storage Queue Data Contributor", "Storage Table Data Contributor"])
  scope                = azurerm_storage_account.func.id
  role_definition_name = each.value
  principal_id         = local.id["api"].principal_id
}

data "external" "function_package" {
  program = [var.python_command, "${local.repo_root}/infra/azure/package_function.py"]
  query   = { repo_root = local.repo_root, out_dir = "${abspath(path.root)}/.build" }
}

resource "azurerm_service_plan" "api" {
  name                = "asp-${var.name}"
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  os_type             = "Linux"
  sku_name            = "FC1"
  tags                = local.tags
}

locals {
  site_origin = trimsuffix(azurerm_storage_account.site.primary_web_endpoint, "/")
  api_env = merge(local.common_env, local.auth_env, {
    AZURE_CLIENT_ID                  = local.id["api"].client_id
    AzureWebJobsStorage__accountName = azurerm_storage_account.func.name
    AzureWebJobsStorage__credential  = "managedidentity"
    AzureWebJobsStorage__clientId    = local.id["api"].client_id
    LakeQueue__queueServiceUri       = trimsuffix(azurerm_storage_account.lake.primary_queue_endpoint, "/")
    LakeQueue__credential            = "managedidentity"
    LakeQueue__clientId              = local.id["api"].client_id
    LAKE_QUEUE_URL                   = azurerm_storage_account.lake.primary_queue_endpoint
    CHAT_QUEUE                       = azurerm_storage_queue.this["chat"].name
    CHAT_MODEL_ID                    = var.foundry.chat_model
    DAILY_QUESTIONS                  = tostring(var.daily_questions)
    MONGODB_URI                      = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.mongodb_uri.versionless_id})"
    }, local.graph_backend == "age" ? {
    AGE_DSN = "host=${azurerm_postgresql_flexible_server.age[0].fqdn} port=5432 dbname=postgres user=${local.id["api"].name} sslmode=require"
    } : {}, local.graph_backend == "neo4j" ? {
    NEO4J_PASSWORD = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.neo4j_password[0].versionless_id})"
  } : {})
}

resource "azurerm_function_app_flex_consumption" "api" {
  name                              = "func-${var.name}-${random_string.suffix.result}"
  location                          = var.location
  resource_group_name               = azurerm_resource_group.this.name
  service_plan_id                   = azurerm_service_plan.api.id
  runtime_name                      = "python"
  runtime_version                   = "3.12"
  storage_container_type            = "blobContainer"
  storage_container_endpoint        = "${azurerm_storage_account.func.primary_blob_endpoint}${azurerm_storage_container.deployments.name}"
  storage_authentication_type       = "UserAssignedIdentity"
  storage_user_assigned_identity_id = local.id["api"].id
  instance_memory_in_mb             = 2048
  maximum_instance_count            = 40
  https_only                        = true
  zip_deploy_file                   = data.external.function_package.result.path
  app_settings                      = local.api_env

  # The system identity resolves Key Vault references; the user-assigned one does everything else.
  identity {
    type         = "SystemAssigned, UserAssigned"
    identity_ids = [local.id["api"].id]
  }
  site_config {
    application_insights_connection_string = azurerm_application_insights.this.connection_string
    minimum_tls_version                    = "1.2"
    cors {
      allowed_origins = [local.site_origin]
    }
  }
  tags       = local.tags
  depends_on = [azurerm_role_assignment.func_host]
}
