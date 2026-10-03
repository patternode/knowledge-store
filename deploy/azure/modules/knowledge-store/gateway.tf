# API Management in front of the MCP tools: one endpoint for Copilot Studio, the Foundry agent
# and any other MCP client. It checks the Entra token before a request reaches the Function App,
# and limits each caller's rate; the Function App checks the token again and derives the
# caller's scope itself, so the gateway is defence in depth, not the only check.
#
# The Function App is an MCP server already (knowledge_store.tools.mcp), so API Management
# passes MCP through as an ordinary HTTP API.

resource "azurerm_api_management" "this" {
  name                = "apim-${var.name}-${random_string.suffix.result}"
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  publisher_name      = var.portal_title
  publisher_email     = var.publisher_email
  sku_name            = var.apim_sku
  tags                = local.tags
}

resource "azurerm_api_management_api" "mcp" {
  name                  = "knowledge-mcp"
  api_management_name   = azurerm_api_management.this.name
  resource_group_name   = azurerm_resource_group.this.name
  display_name          = "Knowledge tools (MCP)"
  description           = "The knowledge graph's tools over the Model Context Protocol (Streamable HTTP)."
  revision              = "1"
  path                  = "mcp"
  protocols             = ["https"]
  service_url           = "https://${azurerm_function_app_flex_consumption.api.default_hostname}/mcp"
  subscription_required = false
}

resource "azurerm_api_management_api_operation" "mcp" {
  for_each            = toset(["POST", "GET", "DELETE"])
  operation_id        = lower(each.key)
  api_name            = azurerm_api_management_api.mcp.name
  api_management_name = azurerm_api_management.this.name
  resource_group_name = azurerm_resource_group.this.name
  display_name        = "MCP ${each.key}"
  method              = each.key
  url_template        = "/"
}

resource "azurerm_api_management_api_policy" "mcp" {
  api_name            = azurerm_api_management_api.mcp.name
  api_management_name = azurerm_api_management.this.name
  resource_group_name = azurerm_resource_group.this.name
  xml_content         = <<-XML
    <policies>
      <inbound>
        <base />
        <validate-azure-ad-token tenant-id="${local.tenant_id}" header-name="Authorization" failed-validation-httpcode="401" failed-validation-error-message="A valid Entra token for the Knowledge Store API is required.">
          <audiences>
            <audience>${azuread_application.api.client_id}</audience>
            <audience>api://${azuread_application.api.client_id}</audience>
          </audiences>
        </validate-azure-ad-token>
        <rate-limit-by-key calls="${var.mcp_calls_per_minute}" renewal-period="60" counter-key='@(context.Request.Headers.GetValueOrDefault("Authorization", "").AsJwt()?.Claims.GetValueOrDefault("oid", "unknown"))' />
      </inbound>
      <backend>
        <base />
      </backend>
      <outbound>
        <base />
      </outbound>
      <on-error>
        <base />
      </on-error>
    </policies>
  XML
}
