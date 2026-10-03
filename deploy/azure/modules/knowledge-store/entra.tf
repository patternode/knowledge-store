# Entra ID: who may call what.
#
#   API        the audience of every token the Function App and API Management accept. Exposes
#              access_as_user (people, through the portal or Copilot Studio) and three app roles:
#              private-reader (people who may read private content), tools.public and
#              tools.private (applications, with client credentials).
#   portal     a single-page app signing people in with PKCE, pre-authorised for the API
#   copilot    the Copilot Studio connector's OAuth client, pre-authorised for the API, so people
#              call the tools as themselves

resource "random_uuid" "entra" {
  for_each = toset(["access_as_user", "private_reader", "tools_public", "tools_private"])
}

resource "azuread_application" "api" {
  display_name     = "${var.name} API"
  sign_in_audience = "AzureADMyOrg"
  owners           = [data.azurerm_client_config.me.object_id]

  api {
    requested_access_token_version = 2
    oauth2_permission_scope {
      id                         = random_uuid.entra["access_as_user"].result
      value                      = "access_as_user"
      type                       = "User"
      admin_consent_display_name = "Use the Knowledge Store as the signed-in user"
      admin_consent_description  = "Read the knowledge graph and ask questions, with the signed-in user's access."
      user_consent_display_name  = "Use the Knowledge Store as you"
      user_consent_description   = "Read the knowledge graph and ask questions, with your access."
    }
  }
  app_role {
    id                   = random_uuid.entra["private_reader"].result
    value                = "private-reader"
    display_name         = "Private reader"
    description          = "Reads content from private sources, and curates ontology drafts."
    allowed_member_types = ["User"]
  }
  app_role {
    id                   = random_uuid.entra["tools_public"].result
    value                = "tools.public"
    display_name         = "Tools, public content"
    description          = "An application calling the knowledge tools over public content."
    allowed_member_types = ["Application"]
  }
  app_role {
    id                   = random_uuid.entra["tools_private"].result
    value                = "tools.private"
    display_name         = "Tools, private content"
    description          = "An application calling the knowledge tools over all content."
    allowed_member_types = ["Application"]
  }

  lifecycle {
    ignore_changes = [identifier_uris] # set by azuread_application_identifier_uri, which needs the client id
  }
}

resource "azuread_application_identifier_uri" "api" {
  application_id = azuread_application.api.id
  identifier_uri = "api://${azuread_application.api.client_id}"
}

resource "azuread_service_principal" "api" {
  client_id = azuread_application.api.client_id
  owners    = [data.azurerm_client_config.me.object_id]
}

resource "azuread_app_role_assignment" "admins" {
  for_each            = toset(var.admin_principal_ids)
  app_role_id         = random_uuid.entra["private_reader"].result
  principal_object_id = each.value
  resource_object_id  = azuread_service_principal.api.object_id
}

resource "azuread_application" "portal" {
  display_name     = "${var.name} portal"
  sign_in_audience = "AzureADMyOrg"
  owners           = [data.azurerm_client_config.me.object_id]
  single_page_application {
    redirect_uris = [azurerm_storage_account.site.primary_web_endpoint]
  }
  required_resource_access {
    resource_app_id = azuread_application.api.client_id
    resource_access {
      id   = random_uuid.entra["access_as_user"].result
      type = "Scope"
    }
  }
}

resource "azuread_service_principal" "portal" {
  client_id = azuread_application.portal.client_id
  owners    = [data.azurerm_client_config.me.object_id]
}

resource "azuread_application" "copilot" {
  display_name     = "${var.name} Copilot Studio connector"
  sign_in_audience = "AzureADMyOrg"
  owners           = [data.azurerm_client_config.me.object_id]
  web {
    redirect_uris = var.copilot_redirect_uris
  }
  required_resource_access {
    resource_app_id = azuread_application.api.client_id
    resource_access {
      id   = random_uuid.entra["access_as_user"].result
      type = "Scope"
    }
  }
}

resource "azuread_service_principal" "copilot" {
  client_id = azuread_application.copilot.client_id
  owners    = [data.azurerm_client_config.me.object_id]
}

# A new secret every 150 days, valid for 180, so an apply in between replaces it before it lapses.
# Paste the new one into the connector after an apply that rotates it.
resource "time_rotating" "copilot" {
  rotation_days = 150
}

resource "azuread_application_password" "copilot" {
  application_id      = azuread_application.copilot.id
  display_name        = "Copilot Studio connector"
  end_date            = timeadd(time_rotating.copilot.id, "4320h")
  rotate_when_changed = { rotation = time_rotating.copilot.id }
}

# The portal and the connector are the API's own clients: nobody is asked to consent to them.
resource "azuread_application_pre_authorized" "api" {
  for_each             = { portal = azuread_application.portal.client_id, copilot = azuread_application.copilot.client_id }
  application_id       = azuread_application.api.id
  authorized_client_id = each.value
  permission_ids       = [random_uuid.entra["access_as_user"].result]
}

locals {
  auth_env = {
    AUTH_ISSUERS   = "https://login.microsoftonline.com/${local.tenant_id}/v2.0"
    AUTH_AUDIENCES = "${azuread_application.api.client_id},api://${azuread_application.api.client_id}"
    AUTH_JWKS_URL  = "https://login.microsoftonline.com/${local.tenant_id}/discovery/v2.0/keys"
  }
}
