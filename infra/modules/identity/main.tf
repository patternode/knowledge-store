# Sign-in for the portal: a Cognito user pool, its managed sign-in domain, one public web
# client (authorisation code with PKCE, no secret), and the groups the portal reads.
#
# Users are created by an administrator only (no self sign-up). The admin user, when
# admin_email is set, receives a temporary password by email from Cognito.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.66" }
  }
}

variable "name" { type = string }
variable "admin_email" {
  type        = string
  default     = ""
  description = "email of the first user; Cognito emails them a temporary password"
}
variable "admin_groups" {
  type        = list(string)
  default     = []
  description = "groups the admin user joins"
}
variable "groups" {
  type        = list(string)
  default     = []
  description = "groups to create, e.g. the portal's private-readers"
}
variable "callback_urls" {
  type        = list(string)
  description = "where sign-in returns: the portal's URL"
}
variable "logout_urls" {
  type    = list(string)
  default = []
}
variable "machine_clients" {
  type = map(object({
    scopes = list(string)
  }))
  default     = {}
  description = <<-EOT
    Applications that authenticate as themselves (OAuth 2.0 client credentials), each with the
    resource-server scopes it may request: agent.invoke (call the agent), tools.public and
    tools.private (what the agent may read for it through the Gateway).
  EOT
}
variable "tags" {
  type    = map(string)
  default = {}
}

data "aws_region" "current" {}
data "aws_caller_identity" "me" {}

resource "aws_cognito_user_pool" "this" {
  name                     = var.name
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  mfa_configuration        = "OFF"
  deletion_protection      = "INACTIVE"

  admin_create_user_config { allow_admin_create_user_only = true }
  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = false
    temporary_password_validity_days = 7
  }
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }
  tags = var.tags
}

resource "aws_cognito_user_pool_domain" "this" {
  domain       = "${var.name}-${data.aws_caller_identity.me.account_id}"
  user_pool_id = aws_cognito_user_pool.this.id
}

resource "aws_cognito_user_pool_client" "web" {
  name                                 = "${var.name}-portal"
  user_pool_id                         = aws_cognito_user_pool.this.id
  generate_secret                      = false
  explicit_auth_flows                  = ["ALLOW_REFRESH_TOKEN_AUTH"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  callback_urls                        = var.callback_urls
  logout_urls                          = length(var.logout_urls) > 0 ? var.logout_urls : var.callback_urls
  supported_identity_providers         = ["COGNITO"]
  id_token_validity                    = 60
  access_token_validity                = 60
  refresh_token_validity               = 12
  token_validity_units {
    id_token      = "minutes"
    access_token  = "minutes"
    refresh_token = "hours"
  }
  prevent_user_existence_errors = "ENABLED"
  enable_token_revocation       = true
}

resource "aws_cognito_user_group" "this" {
  for_each     = toset(concat(var.groups, var.admin_groups))
  name         = each.key
  user_pool_id = aws_cognito_user_pool.this.id
}

resource "aws_cognito_user" "admin" {
  count        = var.admin_email == "" ? 0 : 1
  user_pool_id = aws_cognito_user_pool.this.id
  username     = var.admin_email
  attributes = {
    email          = var.admin_email
    email_verified = "true"
  }
  desired_delivery_mediums = ["EMAIL"]
}

resource "aws_cognito_user_in_group" "admin" {
  for_each     = var.admin_email == "" ? toset([]) : toset(var.admin_groups)
  user_pool_id = aws_cognito_user_pool.this.id
  group_name   = aws_cognito_user_group.this[each.key].name
  username     = aws_cognito_user.admin[0].username
}

# The API the machine clients' scopes belong to. Their access tokens carry client_id and scope,
# no aud, so the Runtime and Gateway authorizers check allowed_clients (and scopes), not audience.
resource "aws_cognito_resource_server" "api" {
  count        = length(var.machine_clients) > 0 ? 1 : 0
  identifier   = var.name
  name         = "${var.name} API"
  user_pool_id = aws_cognito_user_pool.this.id
  scope {
    scope_name        = "agent.invoke"
    scope_description = "Invoke the agent"
  }
  scope {
    scope_name        = "tools.public"
    scope_description = "Read public-scope knowledge through the tools"
  }
  scope {
    scope_name        = "tools.private"
    scope_description = "Read private-scope knowledge through the tools"
  }
}

resource "aws_cognito_user_pool_client" "machine" {
  for_each                             = var.machine_clients
  name                                 = "${var.name}-${each.key}"
  user_pool_id                         = aws_cognito_user_pool.this.id
  generate_secret                      = true
  allowed_oauth_flows                  = ["client_credentials"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = [for s in each.value.scopes : "${var.name}/${s}"]
  explicit_auth_flows                  = ["ALLOW_REFRESH_TOKEN_AUTH"]
  supported_identity_providers         = ["COGNITO"]
  access_token_validity                = 60
  token_validity_units { access_token = "minutes" }
  prevent_user_existence_errors = "ENABLED"
  depends_on                    = [aws_cognito_resource_server.api]
}

locals {
  issuer = "https://cognito-idp.${data.aws_region.current.region}.amazonaws.com/${aws_cognito_user_pool.this.id}"
}

output "user_pool_id" { value = aws_cognito_user_pool.this.id }
output "user_pool_arn" { value = aws_cognito_user_pool.this.arn }
output "client_id" { value = aws_cognito_user_pool_client.web.id }
output "issuer" { value = local.issuer }
output "domain_url" { value = "https://${aws_cognito_user_pool_domain.this.domain}.auth.${data.aws_region.current.region}.amazoncognito.com" }
output "discovery_url" { value = "${local.issuer}/.well-known/openid-configuration" }
output "token_endpoint" { value = "https://${aws_cognito_user_pool_domain.this.domain}.auth.${data.aws_region.current.region}.amazoncognito.com/oauth2/token" }
output "machine_client_ids" { value = { for k, c in aws_cognito_user_pool_client.machine : k => c.id } }
output "machine_client_secrets" {
  value     = { for k, c in aws_cognito_user_pool_client.machine : k => c.client_secret }
  sensitive = true
}
output "scope_prefix" { value = var.name }
