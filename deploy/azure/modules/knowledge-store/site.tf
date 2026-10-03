# The portal page: static files served by a storage account's static website endpoint (HTTPS, no
# server, no cost beyond storage), with a config.json that points it at Entra ID and the API.
# Put Azure Front Door in front for a custom domain, a WAF or response headers.

resource "azurerm_storage_account" "site" {
  name                            = "st${local.short}web"
  location                        = var.location
  resource_group_name             = azurerm_resource_group.this.name
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true
  allow_nested_items_to_be_public = false
  tags                            = local.tags
}

resource "azurerm_storage_account_static_website" "site" {
  storage_account_id = azurerm_storage_account.site.id
  index_document     = "index.html"
}

locals {
  portal_dir   = "${local.repo_root}/portal"
  portal_files = [for f in fileset(local.portal_dir, "**") : f if f != "config.local.json" && f != "config.json"]
  mime = { html = "text/html; charset=utf-8", js = "text/javascript; charset=utf-8", css = "text/css; charset=utf-8",
  json = "application/json", svg = "image/svg+xml", png = "image/png", ico = "image/x-icon" }
  login = "https://login.microsoftonline.com/${local.tenant_id}/oauth2/v2.0"
  # $web is created by enabling the static website, so it has no resource here to refer to.
  web_container_id = "${azurerm_storage_account.site.id}/blobServices/default/containers/$web"
}

resource "azurerm_storage_blob" "site" {
  for_each             = toset(local.portal_files)
  name                 = each.value
  storage_container_id = local.web_container_id
  type                 = "Block"
  source               = "${local.portal_dir}/${each.value}"
  content_md5          = filemd5("${local.portal_dir}/${each.value}")
  content_type         = lookup(local.mime, reverse(split(".", each.value))[0], "application/octet-stream")
  depends_on           = [azurerm_storage_account_static_website.site, time_sleep.deployer_roles]
}

resource "azurerm_storage_blob" "site_config" {
  name                 = "config.json"
  storage_container_id = local.web_container_id
  type                 = "Block"
  content_type         = "application/json"
  source_content = jsonencode({
    mode    = "hosted"
    apiBase = "https://${azurerm_function_app_flex_consumption.api.default_hostname}/api"
    brand   = { name = var.portal_title }
    oidc = {
      authorize      = "${local.login}/authorize"
      token          = "${local.login}/token"
      logout         = "${local.login}/logout"
      logoutStyle    = "oidc"
      clientId       = azuread_application.portal.client_id
      scope          = "api://${azuread_application.api.client_id}/access_as_user openid profile offline_access"
      useAccessToken = true
    }
  })
  depends_on = [azurerm_storage_account_static_website.site, time_sleep.deployer_roles]
}
