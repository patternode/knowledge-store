output "portal_url" {
  value = azurerm_storage_account.site.primary_web_endpoint
}

output "upload_to" {
  description = "where each collection's uploads go: az storage blob upload --auth-mode login --account-name <account> --container-name lake --name landing/<collection>/<file> --file <file>"
  value = { for id in keys(var.collections) : id => {
    account   = azurerm_storage_account.lake.name
    container = azurerm_storage_container.lake.name
    prefix    = "landing/${id}/"
  } }
}

output "lake_uri" {
  description = "LAKE_URI for the CLI (knowledge-store ontology pull/publish)"
  value       = "az://${azurerm_storage_account.lake.name}/${azurerm_storage_container.lake.name}"
}

output "mcp_url" {
  description = "the MCP endpoint for Copilot Studio and agents"
  value       = "${azurerm_api_management.this.gateway_url}/mcp"
}

output "entra" {
  description = "what a client needs to get a token for the API"
  value = {
    tenant_id         = local.tenant_id
    api_client_id     = azuread_application.api.client_id
    api_scope         = "api://${azuread_application.api.client_id}/access_as_user"
    portal_client_id  = azuread_application.portal.client_id
    copilot_client_id = azuread_application.copilot.client_id
    authorization_url = "${local.login}/authorize"
    token_url         = "${local.login}/token"
    refresh_url       = "${local.login}/token"
  }
}

output "copilot_client_secret" {
  description = "the Copilot Studio connector's client secret (terraform output -raw copilot_client_secret)"
  value       = azuread_application_password.copilot.value
  sensitive   = true
}

output "resource_group" {
  value = azurerm_resource_group.this.name
}

output "graph_backend" {
  value = local.graph_backend
}
