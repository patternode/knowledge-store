# MongoDB (always: the chat state; with document_projection, the portal's projection too) and the
# graph (with graph = true).
#
#   native  Cosmos DB for MongoDB, serverless (idles at close to nothing), and PostgreSQL with
#           Apache AGE, signed in to with Entra ID (no database password exists)
#   common  your MongoDB (mongodb_uri) and your Neo4j (neo4j, neo4j_password)

resource "azurerm_cosmosdb_account" "mongo" {
  count                = var.profile == "native" ? 1 : 0
  name                 = "cosmos-${local.short}"
  location             = var.location
  resource_group_name  = azurerm_resource_group.this.name
  offer_type           = "Standard"
  kind                 = "MongoDB"
  mongo_server_version = "7.0"
  minimal_tls_version  = "Tls12"
  capabilities {
    name = "EnableServerless"
  }
  capabilities {
    name = "EnableMongo"
  }
  capabilities {
    name = "DisableRateLimitingResponses" # retry throttled requests server side, not in the client
  }
  consistency_policy {
    consistency_level = "Session"
  }
  geo_location {
    location          = var.location
    failover_priority = 0
  }
  tags = local.tags
}

resource "azurerm_cosmosdb_mongo_database" "this" {
  count               = var.profile == "native" ? 1 : 0
  name                = "knowledge_store"
  resource_group_name = azurerm_resource_group.this.name
  account_name        = azurerm_cosmosdb_account.mongo[0].name
}

# Cosmos DB for MongoDB (RU) authenticates with its key, so the connection string is a secret.
resource "azurerm_key_vault_secret" "mongodb_uri" {
  name         = "mongodb-uri"
  key_vault_id = azurerm_key_vault.this.id
  value        = var.profile == "native" ? azurerm_cosmosdb_account.mongo[0].primary_mongodb_connection_string : var.mongodb_uri
  content_type = "text/plain"
  depends_on   = [time_sleep.deployer_roles]
}

resource "azurerm_key_vault_secret" "neo4j_password" {
  count        = local.graph_backend == "neo4j" ? 1 : 0
  name         = "neo4j-password"
  key_vault_id = azurerm_key_vault.this.id
  value        = var.neo4j_password
  content_type = "text/plain"
  depends_on   = [time_sleep.deployer_roles]
}

# --- AGE -------------------------------------------------------------------------------------------

resource "azurerm_postgresql_flexible_server" "age" {
  count                         = local.graph_backend == "age" ? 1 : 0
  name                          = "psql-${local.short}"
  location                      = var.location
  resource_group_name           = azurerm_resource_group.this.name
  version                       = "16"
  sku_name                      = "B_Standard_B1ms"
  storage_mb                    = 32768
  backup_retention_days         = 7
  public_network_access_enabled = true
  authentication {
    active_directory_auth_enabled = true
    password_auth_enabled         = false
    tenant_id                     = local.tenant_id
  }
  tags = local.tags
  lifecycle {
    ignore_changes = [zone] # Azure picks a zone; moving it is not this module's business
  }
}

# Azure services only (Container Apps and Functions egress); sign-in is Entra-only either way.
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure" {
  count            = local.graph_backend == "age" ? 1 : 0
  name             = "azure-services"
  server_id        = azurerm_postgresql_flexible_server.age[0].id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# AGE must be allow-listed and preloaded; the server restarts to apply the preload.
resource "azurerm_postgresql_flexible_server_configuration" "age" {
  for_each  = local.graph_backend == "age" ? { "azure.extensions" = "AGE", "shared_preload_libraries" = "age,pg_stat_statements" } : {}
  name      = each.key
  server_id = azurerm_postgresql_flexible_server.age[0].id
  value     = each.value
}

# The pipeline is the server's Entra administrator: it creates the extension and each loaded
# graph, and grants the API's identity read access to them (AGE_READERS).
resource "azurerm_postgresql_flexible_server_active_directory_administrator" "pipeline" {
  count               = local.graph_backend == "age" ? 1 : 0
  server_name         = azurerm_postgresql_flexible_server.age[0].name
  resource_group_name = azurerm_resource_group.this.name
  tenant_id           = local.tenant_id
  object_id           = local.id["pipeline"].principal_id
  principal_name      = local.id["pipeline"].name
  principal_type      = "ServicePrincipal"
}
